# tests/test_device_upload.py
#
# End-to-end tests for the camera's event-clip upload: real ffmpeg-made video
# segments go in, one playable MP4 must come out in the gallery.

import hashlib
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import conftest                                   # for TestSessionLocal
from app.core.config import settings
from app.models.clip_upload import ClipUpload, ClipUploadStatus
from app.services import clip_storage

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def media_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "MEDIA_MIN_FREE_BYTES", 0)
    return Path(settings.MEDIA_ROOT)


@pytest.fixture(scope="module")
def segments(tmp_path_factory):
    """Three 2-second H.264 MPEG-TS pieces with identical encoder settings."""
    d = tmp_path_factory.mktemp("segs")
    out = []
    for i in range(3):
        f = d / f"s{i}.ts"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=15:duration=2",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-g", "15",
             "-f", "mpegts", str(f)],
            check=True,
        )
        out.append(f.read_bytes())
    return out


@pytest.fixture()
def device(client, auth_headers):
    r = client.post("/api/device/key", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["device_key"].startswith("vgx_")
    return {"X-Device-Id": body["device_id"], "X-Device-Key": body["device_key"]}


_counter = {"n": 0}
def new_clip_id():
    _counter["n"] += 1
    return f"testclip-{_counter['n']:04d}"


def put_seg(client, device, clip, idx, data, **extra):
    return client.put(f"/api/device/clips/{clip}/segments/{idx}", content=data,
                      headers={**device, "Content-Type": "application/octet-stream", **extra})


def start(client, device, clip, **kw):
    return client.post("/api/device/clips", json={"client_clip_id": clip, **kw}, headers=device)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=format_name,duration",
         "-of", "default=noprint_wrappers=1", str(path)],
        capture_output=True, text=True, check=True).stdout
    kv = dict(line.split("=", 1) for line in out.strip().splitlines())
    return kv["format_name"], float(kv["duration"])


# ── Authentication ────────────────────────────────────────────────────────────
def test_key_endpoint_needs_owner_login(client):
    assert client.post("/api/device/key").status_code in (401, 403)


def test_device_endpoints_reject_bad_credentials(client, device):
    clip = new_clip_id()
    assert client.post("/api/device/clips", json={"client_clip_id": clip}).status_code == 401
    bad_key = {**device, "X-Device-Key": "vgx_wrong"}
    assert start(client, bad_key, clip).status_code == 401
    unknown = {**device, "X-Device-Id": "no-such-device"}
    assert start(client, unknown, clip).status_code == 401


def test_rotating_key_disables_old_key(client, auth_headers):
    first = client.post("/api/device/key", headers=auth_headers).json()
    h1 = {"X-Device-Id": first["device_id"], "X-Device-Key": first["device_key"]}
    assert start(client, h1, new_clip_id()).status_code == 200
    second = client.post("/api/device/key", headers=auth_headers).json()
    assert start(client, h1, new_clip_id()).status_code == 401
    h2 = {"X-Device-Id": second["device_id"], "X-Device-Key": second["device_key"]}
    assert start(client, h2, new_clip_id()).status_code == 200


# ── Happy path, retries, missing pieces ───────────────────────────────────────
def test_full_flow_produces_playable_gallery_item(client, device, auth_headers, segments, media_root, tmp_path):
    clip = new_clip_id()
    r = start(client, device, clip, trigger_reason="door_opened",
              recorded_at=datetime.now(timezone.utc).isoformat())
    assert r.status_code == 200 and r.json()["status"] == "uploading"
    assert start(client, device, clip).json()["status"] == "uploading"        # repeat start = same clip

    sha = lambda b: hashlib.sha256(b).hexdigest()
    assert put_seg(client, device, clip, 0, segments[0], **{"X-Segment-SHA256": sha(segments[0])}).status_code == 200
    r = put_seg(client, device, clip, 2, segments[2])
    assert r.json()["segments_received"] == [0, 2]

    # finishing with a piece missing must say exactly which one
    r = client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 3}, headers=device)
    assert r.status_code == 409 and r.json()["detail"]["missing"] == [1]

    assert put_seg(client, device, clip, 1, segments[1]).status_code == 200
    r = client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 3}, headers=device)
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "complete" and done["media_id"]
    assert done["media"]["source"] == "event" and done["media"]["trigger_reason"] == "door_opened"
    media_id = done["media_id"]

    # repeating finish must NOT create a second gallery item
    again = client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 3}, headers=device).json()
    assert again["media_id"] == media_id

    # it is in the normal gallery the app reads...
    gal = client.get("/api/vehicle/camera/media?media_type=recording", headers=auth_headers).json()
    item = next(m for m in gal["items"] if m["id"] == media_id)
    assert item["source"] == "event"
    assert sum(1 for m in gal["items"] if m.get("trigger_reason") == "door_opened") >= 1

    # ...and the file the app downloads is one real MP4 of about 6 seconds
    f = client.get(f"/api/vehicle/camera/media/{media_id}/file", headers=auth_headers)
    assert f.status_code == 200
    p = tmp_path / "out.mp4"; p.write_bytes(f.content)
    fmt, dur = probe(p)
    assert "mp4" in fmt
    assert 5.0 < dur < 7.5, dur

    # segment folder is cleaned up
    assert not clip_storage.clip_dir(item_vehicle_id(client, auth_headers), clip).exists()


def item_vehicle_id(client, auth_headers):
    return client.get("/api/vehicle/status", headers=auth_headers).json()["id"]


def test_resending_a_segment_is_harmless(client, device, segments):
    clip = new_clip_id(); start(client, device, clip)
    a = put_seg(client, device, clip, 0, segments[0]).json()
    b = put_seg(client, device, clip, 0, segments[0]).json()
    assert a["segments_received"] == b["segments_received"] == [0]
    assert a["bytes_received"] == b["bytes_received"] == len(segments[0])
    # status endpoint tells a restarted camera what it still has to send
    s = client.get(f"/api/device/clips/{clip}", headers=device).json()
    assert s["segments_received"] == [0]


def test_partial_finish_joins_what_arrived(client, device, segments):
    clip = new_clip_id(); start(client, device, clip)
    put_seg(client, device, clip, 0, segments[0]); put_seg(client, device, clip, 2, segments[2])
    r = client.post(f"/api/device/clips/{clip}/finish",
                    json={"total_segments": 3, "allow_partial": True}, headers=device)
    assert r.status_code == 200, r.text
    assert 3.0 < r.json()["media"]["duration_seconds"] < 5.0


# ── Safety limits ─────────────────────────────────────────────────────────────
def test_checksum_mismatch_rejected_and_not_stored(client, device, segments):
    clip = new_clip_id(); start(client, device, clip)
    r = put_seg(client, device, clip, 0, segments[0], **{"X-Segment-SHA256": "0" * 64})
    assert r.status_code == 422
    assert client.get(f"/api/device/clips/{clip}", headers=device).json()["segments_received"] == []


def test_oversize_segment_rejected_and_no_leftovers(client, device, segments, monkeypatch, media_root):
    monkeypatch.setattr(settings, "CLIP_MAX_SEGMENT_BYTES", 100)
    clip = new_clip_id(); start(client, device, clip)
    assert put_seg(client, device, clip, 0, segments[0]).status_code == 413
    leftovers = [p for p in media_root.rglob("*") if p.is_file()]
    assert leftovers == [], leftovers


def test_empty_segment_and_bad_index_rejected(client, device):
    clip = new_clip_id(); start(client, device, clip)
    assert put_seg(client, device, clip, 0, b"").status_code == 422
    assert put_seg(client, device, clip, settings.CLIP_MAX_SEGMENTS, b"x").status_code == 422


def test_bad_clip_ids_rejected(client, device):
    assert start(client, device, "../../etc/passwd").status_code == 422
    assert start(client, device, "short").status_code == 422
    assert client.get("/api/device/clips/has%20space%20in%20it", headers=device).status_code == 422
    assert client.get("/api/device/clips/doesnotexist-0001", headers=device).status_code == 404


def test_clips_are_private_to_their_own_vehicle(client, device, segments):
    clip = new_clip_id(); start(client, device, clip)
    # a second owner with their own vehicle and key
    client.post("/api/auth/register", json={"email": "other@smartguard.com", "phone": "+1111111111",
                                           "full_name": "Other", "password": "secure123"})
    tok = client.post("/api/auth/login", json={"email": "other@smartguard.com", "password": "secure123"}).json()["access_token"]
    oh = {"Authorization": f"Bearer {tok}"}
    client.post("/api/vehicle/register", json={"name": "Other", "reg_number": "OTHER-1", "device_id": "ESP32-OTHER"}, headers=oh)
    k = client.post("/api/device/key", headers=oh).json()
    other = {"X-Device-Id": k["device_id"], "X-Device-Key": k["device_key"]}
    assert client.get(f"/api/device/clips/{clip}", headers=other).status_code == 404
    assert put_seg(client, other, clip, 0, segments[0]).status_code == 404


# ── Failure handling ──────────────────────────────────────────────────────────
def test_abort_then_restart(client, device, segments, auth_headers):
    clip = new_clip_id(); start(client, device, clip); put_seg(client, device, clip, 0, segments[0])
    r = client.delete(f"/api/device/clips/{clip}", headers=device)
    assert r.status_code == 200 and r.json()["status"] == "aborted"
    assert put_seg(client, device, clip, 0, segments[0]).status_code == 409
    r = start(client, device, clip)                                        # same id, start over
    assert r.json()["status"] == "uploading" and r.json()["segments_received"] == []


def test_corrupt_segment_fails_cleanly_then_retry_succeeds(client, device, segments):
    clip = new_clip_id(); start(client, device, clip)
    put_seg(client, device, clip, 0, b"this is not video data at all" * 50)
    r = client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 1}, headers=device)
    assert r.status_code == 500
    assert client.get(f"/api/device/clips/{clip}", headers=device).json()["status"] == "failed"
    put_seg(client, device, clip, 0, segments[0])                          # camera resends a good piece
    r = client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 1}, headers=device)
    assert r.status_code == 200 and r.json()["status"] == "complete"


def test_cannot_abort_a_clip_already_in_the_gallery(client, device, segments):
    clip = new_clip_id(); start(client, device, clip); put_seg(client, device, clip, 0, segments[0])
    client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 1}, headers=device)
    assert client.delete(f"/api/device/clips/{clip}", headers=device).status_code == 409


# ── Housekeeping ──────────────────────────────────────────────────────────────
def test_sane_time():
    now = datetime.now(timezone.utc)
    assert abs((clip_storage.sane_time(datetime(1970, 1, 1, tzinfo=timezone.utc)) - now).total_seconds()) < 5
    assert abs((clip_storage.sane_time(now + timedelta(days=3)) - now).total_seconds()) < 5
    recent = now - timedelta(hours=2)
    assert clip_storage.sane_time(recent) == recent
    assert abs((clip_storage.sane_time(None) - now).total_seconds()) < 5


def test_stale_upload_sweep(client, device, segments, auth_headers, monkeypatch):
    monkeypatch.setattr(clip_storage, "SessionLocal", conftest.TestSessionLocal)
    clip = new_clip_id(); start(client, device, clip); put_seg(client, device, clip, 0, segments[0])
    vid = item_vehicle_id(client, auth_headers)
    assert clip_storage.clip_dir(vid, clip).exists()

    db = conftest.TestSessionLocal()
    row = db.query(ClipUpload).filter(ClipUpload.client_clip_id == clip).one()
    row.updated_at = datetime.now(timezone.utc) - timedelta(hours=settings.CLIP_STALE_HOURS + 1)
    db.commit(); db.close()

    clip_storage.sweep_stale_clip_uploads()
    assert not clip_storage.clip_dir(vid, clip).exists()
    assert client.get(f"/api/device/clips/{clip}", headers=device).json()["status"] == "aborted"


# ── Step 3: gallery refresh notification ──────────────────────────────────────
def test_finish_notifies_app_once(client, device, segments, monkeypatch):
    import app.routes.device as device_routes
    calls = []
    monkeypatch.setattr(device_routes, "notify_clip_ready", lambda vid, payload: calls.append((vid, payload)))
    clip = new_clip_id(); start(client, device, clip, trigger_reason="glass_break")
    put_seg(client, device, clip, 0, segments[0])
    assert client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 1}, headers=device).status_code == 200
    client.post(f"/api/device/clips/{clip}/finish", json={"total_segments": 1}, headers=device)   # repeat
    assert len(calls) == 1
    assert calls[0][1]["source"] == "event" and calls[0][1]["trigger_reason"] == "glass_break"
    assert calls[0][1]["media_id"]


def test_notify_clip_ready_broadcasts(monkeypatch):
    from app.services import mqtt_handlers
    got = []
    async def fake(vid, t, p): got.append((vid, t, p))
    monkeypatch.setattr(mqtt_handlers, "_broadcast_event", fake)
    monkeypatch.setattr(mqtt_handlers, "_broadcast_threadsafe", lambda c: __import__("asyncio").run(c))
    monkeypatch.setattr(mqtt_handlers, "SessionLocal", conftest.TestSessionLocal)
    pushes = []
    monkeypatch.setattr(mqtt_handlers, "_send_push_notification", lambda db, v, t, b: pushes.append((t, b)))
    mqtt_handlers.notify_clip_ready(1, {"media_id": 9, "trigger_reason": "door_opened"})
    assert got == [(1, "clip_ready", {"media_id": 9, "trigger_reason": "door_opened"})]
    assert pushes and "door opened" in pushes[0][1]