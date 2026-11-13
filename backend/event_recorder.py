# event_recorder.py  —  sits next to simulator.py
#
# Simulates what the REAL camera firmware will do for EVENT recording:
#
#   suspicious event ──► record to local "SD card" in ~N-second segments
#                        (up to EVENT_CLIP_SECONDS in total)
#   user opens stream ─► finish/close the clip, stream FIRST, upload AFTER
#   stream ended / idle ► upload segments to the backend, then delete locally
#
# It talks to the backend only through the /api/device/clips endpoints and
# reports its state on MQTT (sg/<device>/camera/state). Everything that is
# written to the SD folder survives a restart, so an interrupted recording or
# upload is picked up again on the next start (like a real power cut).
#
# Config (environment / .env):
#   BACKEND_URL              e.g. https://vigilx.duckdns.org      (required for upload)
#   DEVICE_KEY               the vgx_... key from POST /api/device/key
#   EVENT_CLIP_SECONDS       max length of one clip            (default 40; real firmware: 300)
#   EVENT_SEGMENT_SECONDS    length of one uploaded piece      (default 10; real firmware: 30)
#   EVENT_COOLDOWN_SECONDS   min gap between two event clips   (default 60)
#   SD_DIR                   folder acting as the SD card      (default ./sim_sdcard)

import hashlib
import json
import logging
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger("event_recorder")

FPS = 10
WIDTH = 320
HEIGHT = 240


class EventRecorder:
    def __init__(
        self,
        device_id: str,
        publish_state,
        backend_url: str | None,
        device_key: str | None,
        sd_dir: str | None = None,
        clip_seconds: float | None = None,
        segment_seconds: float | None = None,
        cooldown_seconds: float | None = None,
        realtime: bool = True,
    ):
        self.device_id = device_id
        self._publish = publish_state  # callable(dict) -> publishes camera/state on MQTT
        self.backend_url = (backend_url or "").rstrip("/")
        self.device_key = device_key or ""
        self.sd_dir = Path(sd_dir or os.getenv("SD_DIR", "./sim_sdcard"))
        self.clip_seconds = float(
            clip_seconds if clip_seconds is not None else os.getenv("EVENT_CLIP_SECONDS", 40)
        )
        self.segment_seconds = float(
            segment_seconds
            if segment_seconds is not None
            else os.getenv("EVENT_SEGMENT_SECONDS", 10)
        )
        self.cooldown = float(
            cooldown_seconds
            if cooldown_seconds is not None
            else os.getenv("EVENT_COOLDOWN_SECONDS", 60)
        )
        self.realtime = realtime
        self.sd_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._streaming = False
        self._recording = False
        self._uploading_clip: str | None = None
        self._stop_recording = threading.Event()
        self._wake_uploader = threading.Event()
        self._last_event_at = 0.0
        self._rec_thread: threading.Thread | None = None
        self._closed = False
        self._recovered = False

        threading.Thread(target=self._upload_loop, daemon=True, name="event-uploader").start()

    # ── Public API (called from simulator.py) ────────────────────────────────
    def start(self):
        """
        Call whenever MQTT (re)connects. The first time it also recovers clips left
        on the SD card by a previous run; every time it re-announces the current
        state, so the backend/app are never left with a stale one.
        """
        if not self._recovered:
            self._recovered = True
            self._recover_unfinished()
        self._report(self._current_state())
        self._wake_uploader.set()

    def _current_state(self) -> str:
        if self._streaming:
            return "streaming"
        if self._recording:
            return "recording"
        if self._uploading_clip:
            return "uploading"
        return "idle"

    def trigger(self, reason: str) -> bool:
        """A suspicious event happened. Starts a clip unless busy / cooling down / streaming."""
        with self._lock:
            if self._closed:
                return False
            if self._streaming:
                logger.info("🎬 Event ignored — live stream is open (user is watching)")
                return False
            if self._recording:
                return False
            if time.time() - self._last_event_at < self.cooldown:
                logger.info("🎬 Event ignored — cooling down")
                return False
            self._recording = True
            self._last_event_at = time.time()
            self._stop_recording.clear()

        clip_id = f"evt-{datetime.now(UTC):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
        self._rec_thread = threading.Thread(
            target=self._record, args=(clip_id, reason), daemon=True, name="event-recorder"
        )
        self._rec_thread.start()
        return True

    def on_stream_started(self, finalize_recording: bool = True):
        """User opened the live stream: close any clip being recorded and pause uploads."""
        with self._lock:
            self._streaming = True
            was_recording = self._recording
        if was_recording and finalize_recording:
            logger.info("🎬 Stream requested while recording — finalizing clip first")
            self._stop_recording.set()
            t = self._rec_thread
            if t:
                t.join(timeout=15)
        self._report("streaming")

    def on_stream_ended(self):
        with self._lock:
            if not self._streaming:
                return
            self._streaming = False
        self._report("idle")
        # Stream-first is over — upload what is waiting, after a short pause so a
        # quick "close and reopen the stream" does not start an upload in between.
        t = threading.Timer(3.0, self._wake_uploader.set)
        t.daemon = True
        t.start()

    def close(self):
        with self._lock:
            self._closed = True
        self._stop_recording.set()
        self._wake_uploader.set()

    # ── Recording ────────────────────────────────────────────────────────────
    def _clip_dir(self, clip_id: str) -> Path:
        return self.sd_dir / clip_id

    def _write_manifest(self, _dir_name: str, **updates):
        d = self._clip_dir(_dir_name)
        p = d / "manifest.json"
        m = json.loads(p.read_text()) if p.exists() else {}
        m.update(updates)
        tmp = d / "manifest.json.tmp"
        tmp.write_text(json.dumps(m))
        os.replace(tmp, p)  # atomic, like a safe SD write
        return m

    def _record(self, clip_id: str, reason: str):
        d = self._clip_dir(clip_id)
        d.mkdir(parents=True, exist_ok=True)
        recorded_at = datetime.now(UTC).isoformat()
        self._write_manifest(
            clip_id,
            clip_id=clip_id,
            reason=reason,
            recorded_at=recorded_at,
            finalized=False,
            segments=0,
            duration=0.0,
            uploaded=False,
        )
        logger.info(f"🔴 Recording started — clip={clip_id} reason={reason}")
        self._report("recording", clip_id=clip_id, reason=reason, elapsed_s=0)

        seg_index, elapsed, frame_no = 0, 0.0, 0
        last_report = 0.0
        try:
            while elapsed < self.clip_seconds and not self._stop_recording.is_set():
                seg_len = min(self.segment_seconds, self.clip_seconds - elapsed)
                frames = self._write_segment(
                    d / f"seg_{seg_index:05d}.ts",
                    seg_len,
                    reason,
                    frame_no,
                    elapsed,
                    clip_id,
                    last_report,
                )
                frame_no += frames
                elapsed += frames / FPS
                if frames == 0:
                    break
                seg_index += 1
                self._write_manifest(clip_id, segments=seg_index, duration=round(elapsed, 2))
                last_report = elapsed
        except Exception as e:
            logger.error(f"Recording error — clip={clip_id}: {e!r}")
        finally:
            self._write_manifest(
                clip_id, finalized=True, segments=seg_index, duration=round(elapsed, 2)
            )
            with self._lock:
                self._recording = False
            logger.info(
                f"⏹️  Recording finished — clip={clip_id} segments={seg_index} {elapsed:.1f}s"
            )
            if not self._streaming:
                self._report("idle")
            self._wake_uploader.set()

    def _write_segment(
        self,
        path: Path,
        seconds: float,
        reason: str,
        frame_no: int,
        elapsed: float,
        clip_id: str,
        last_report: float,
    ) -> int:
        """Encode up to `seconds` of video into one MPEG-TS file. Stops early on stop request."""
        container = av.open(str(path) + ".part", mode="w", format="mpegts")
        stream = container.add_stream("libx264", rate=FPS)
        stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
        # IDENTICAL settings for every segment — required for a lossless join.
        stream.options = {"preset": "ultrafast", "g": str(FPS), "tune": "zerolatency"}
        stream.time_base = Fraction(1, 90000)

        n_target = int(round(seconds * FPS))
        n = 0
        t0 = time.time()
        try:
            while n < n_target and not self._stop_recording.is_set():
                frame = av.VideoFrame.from_ndarray(self._draw(frame_no + n, reason), format="rgb24")
                frame.pts = int(n * 90000 / FPS)
                frame.time_base = Fraction(1, 90000)
                for pkt in stream.encode(frame):
                    container.mux(pkt)
                n += 1
                if elapsed + n / FPS - last_report >= 5:
                    last_report = elapsed + n / FPS
                    self._report(
                        "recording", clip_id=clip_id, reason=reason, elapsed_s=round(last_report, 1)
                    )
                if self.realtime:
                    delay = t0 + n / FPS - time.time()
                    if delay > 0:
                        time.sleep(delay)
            for pkt in stream.encode():
                container.mux(pkt)
        finally:
            container.close()
        if n == 0:
            Path(str(path) + ".part").unlink(missing_ok=True)
            return 0
        os.replace(str(path) + ".part", path)
        return n

    @staticmethod
    def _draw(i: int, reason: str) -> np.ndarray:
        img = Image.new("RGB", (WIDTH, HEIGHT), (20, 24, 32))
        dr = ImageDraw.Draw(img)
        x = (i * 4) % (WIDTH - 40)
        dr.rectangle([x, 90, x + 40, 150], fill=(220, 60, 60))
        dr.text((8, 8), f"EVENT: {reason}", fill=(255, 255, 255))
        dr.text((8, 24), datetime.now(UTC).strftime("%H:%M:%S UTC"), fill=(180, 220, 255))
        dr.text((8, HEIGHT - 20), f"frame {i}", fill=(150, 150, 150))
        return np.asarray(img)

    # ── Recovery after power loss ────────────────────────────────────────────
    def _recover_unfinished(self):
        for d in sorted(self.sd_dir.glob("evt-*")):
            for part in d.glob("*.part"):
                part.unlink(missing_ok=True)  # half-written segment — unusable
            mf = d / "manifest.json"
            if not mf.exists():
                shutil.rmtree(d, ignore_errors=True)
                continue
            segs = sorted(d.glob("seg_*.ts"))
            m = json.loads(mf.read_text())
            if not m.get("finalized"):
                logger.info(f"♻️  Recovering interrupted clip {d.name} ({len(segs)} segments)")
                self._write_manifest(d.name, finalized=True, segments=len(segs))

    # ── Upload ───────────────────────────────────────────────────────────────
    def _pending(self) -> list[Path]:
        out = []
        for d in sorted(self.sd_dir.glob("evt-*")):
            mf = d / "manifest.json"
            if mf.exists():
                m = json.loads(mf.read_text())
                if m.get("finalized") and not m.get("uploaded"):
                    out.append(d)
        return out

    def _upload_loop(self):
        backoff = 5
        while True:
            self._wake_uploader.wait(timeout=30)
            self._wake_uploader.clear()
            if self._closed:
                return
            if self._streaming or self._recording or not self.backend_url or not self.device_key:
                continue
            did_work = False
            for d in self._pending():
                if self._streaming or self._recording or self._closed:
                    break
                did_work = True
                ok = self._upload_clip(d)
                if not ok:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    self._wake_uploader.set()  # retry later
                    break
                backoff = 5
            if did_work and not self._streaming and not self._recording:
                self._report("idle")

    def _http(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict | None = None,
        timeout: float = 60,
    ):
        req = urllib.request.Request(self.backend_url + path, data=body, method=method)
        req.add_header("X-Device-Id", self.device_id)
        req.add_header("X-Device-Key", self.device_key)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"detail": raw[:200].decode("utf-8", "replace")}

    def _upload_clip(self, d: Path) -> bool:
        m = json.loads((d / "manifest.json").read_text())
        clip_id = m["clip_id"]
        segs = sorted(d.glob("seg_*.ts"))
        total = len(segs)
        if total == 0:
            shutil.rmtree(d, ignore_errors=True)
            return True
        self._uploading_clip = clip_id
        logger.info(f"⬆️  Uploading clip {clip_id} — {total} segments")
        try:
            code, body = self._http(
                "POST",
                "/api/device/clips",
                json.dumps(
                    {
                        "client_clip_id": clip_id,
                        "trigger_reason": m.get("reason"),
                        "recorded_at": m.get("recorded_at"),
                    }
                ).encode(),
                {"Content-Type": "application/json"},
            )
            if code == 401:
                logger.error("⬆️  Backend rejected the device key (401) — check DEVICE_KEY")
                return False
            if code != 200:
                logger.warning(f"⬆️  start failed {code}: {body}")
                return False
            if body.get("status") == "complete":
                return self._mark_done(d)

            have = set(body.get("segments_received", []))
            for i, f in enumerate(segs):
                if i in have:
                    continue
                if self._streaming or self._closed:  # stream-first: pause, resume later
                    logger.info("⬆️  Upload paused — stream opened")
                    return True
                data = f.read_bytes()
                code, body = self._http(
                    "PUT",
                    f"/api/device/clips/{clip_id}/segments/{i}",
                    data,
                    {
                        "Content-Type": "application/octet-stream",
                        "X-Segment-SHA256": hashlib.sha256(data).hexdigest(),
                    },
                    timeout=120,
                )
                if code != 200:
                    logger.warning(f"⬆️  segment {i} failed {code}: {body}")
                    return False
                self._report(
                    "uploading",
                    clip_id=clip_id,
                    reason=m.get("reason"),
                    segments_uploaded=i + 1,
                    segments_total=total,
                )

            code, body = self._http(
                "POST",
                f"/api/device/clips/{clip_id}/finish",
                json.dumps(
                    {"total_segments": total, "duration_seconds": m.get("duration")}
                ).encode(),
                {"Content-Type": "application/json"},
                timeout=240,
            )
            if code == 409 and isinstance(body.get("detail"), dict):
                logger.warning(
                    f"⬆️  server is missing {body['detail'].get('missing')} — will resend"
                )
                return False
            if code != 200:
                logger.warning(f"⬆️  finish failed {code}: {body}")
                return False
            logger.info(f"✅ Clip {clip_id} is in the gallery (media_id={body.get('media_id')})")
            return self._mark_done(d)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            logger.warning(f"⬆️  network problem, will retry: {e!r}")
            return False
        finally:
            self._uploading_clip = None

    def _mark_done(self, d: Path) -> bool:
        shutil.rmtree(d, ignore_errors=True)  # free the SD card
        return True

    # ── State reporting ──────────────────────────────────────────────────────
    def _report(self, state: str, **extra):
        try:
            self._publish({"state": state, **extra})
        except Exception as e:
            logger.debug(f"state publish failed: {e!r}")
