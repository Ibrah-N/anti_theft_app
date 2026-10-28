# app/services/clip_storage.py
#
# Disk-side helpers for event clips uploaded by the camera in numbered
# segments. Segments live in
#
#     MEDIA_ROOT/<vehicle_id>/_clips/<client_clip_id>/seg_00000.bin ...
#
# until the camera says "finish". They are then joined into one MP4 (without
# re-encoding — ffmpeg just copies the video) and the segment folder is deleted.

import logging
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.clip_upload import ClipUpload, ClipUploadStatus

logger = logging.getLogger(__name__)

# The clip id becomes part of a folder name, so it is restricted to a safe
# alphabet (no slashes, no dots) — see also the same pattern on the routes.
CLIP_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
_CLIP_ID_RE     = re.compile(CLIP_ID_PATTERN)
_SEGMENT_RE     = re.compile(r"^seg_(\d{5})\.bin$")

JOIN_TIMEOUT_SECONDS = 180


class ClipJoinError(Exception):
    """ffmpeg could not join the segments into a playable file."""


# ── Paths ─────────────────────────────────────────────────────────────────────
def media_dir(vehicle_id: int) -> Path:
    d = Path(settings.MEDIA_ROOT) / str(vehicle_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def clip_dir(vehicle_id: int, clip_id: str, create: bool = False) -> Path:
    if not _CLIP_ID_RE.match(clip_id):          # defence in depth — never build a path from unchecked input
        raise ValueError("invalid clip id")
    d = Path(settings.MEDIA_ROOT) / str(vehicle_id) / "_clips" / clip_id
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def segment_path(vehicle_id: int, clip_id: str, index: int) -> Path:
    return clip_dir(vehicle_id, clip_id) / f"seg_{index:05d}.bin"


def list_segments(vehicle_id: int, clip_id: str) -> dict[int, int]:
    """{segment_index: size_in_bytes} for every fully received segment."""
    d = clip_dir(vehicle_id, clip_id)
    result: dict[int, int] = {}
    if not d.is_dir():
        return result
    for f in d.iterdir():
        m = _SEGMENT_RE.match(f.name)
        if m and f.is_file():
            result[int(m.group(1))] = f.stat().st_size
    return result


def remove_clip_dir(vehicle_id: int, clip_id: str):
    shutil.rmtree(clip_dir(vehicle_id, clip_id), ignore_errors=True)


def check_disk_space():
    root = Path(settings.MEDIA_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < settings.MEDIA_MIN_FREE_BYTES:
        raise HTTPException(
            status_code=507,
            detail="Server storage is critically low — try again later",
        )


# ── Joining ───────────────────────────────────────────────────────────────────
def join_segments(segment_files: list[Path], out_path: Path):
    """
    Concatenate segments into one MP4 with ffmpeg's concat demuxer.
    `-c copy` = no re-encoding, so it is fast and loses no quality. This needs
    all segments to share the same codec settings, which they do because the
    same camera encoder produced them.
    """
    if shutil.which("ffmpeg") is None:
        raise ClipJoinError("ffmpeg is not installed on the server")

    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "list.txt"
        list_file.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in segment_files),
            encoding="utf-8",
        )
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", "-movflags", "+faststart",
            str(out_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=JOIN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            out_path.unlink(missing_ok=True)
            raise ClipJoinError("ffmpeg timed out while joining segments")

    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        out_path.unlink(missing_ok=True)
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        raise ClipJoinError("ffmpeg failed: " + " | ".join(tail))


def probe_duration(path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None
    except (subprocess.TimeoutExpired, ValueError):
        return None


# ── Time sanity ───────────────────────────────────────────────────────────────
def sane_time(dt: datetime | None) -> datetime:
    """
    The camera's clock may be wrong (e.g. before it has synced time, a device
    often thinks it is 1970). A bad timestamp would sort the clip to the wrong
    place in the gallery and make the 30-day cleanup delete it immediately, so
    anything implausible falls back to "now".
    """
    now = datetime.now(timezone.utc)
    if dt is None:
        return now
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt > now + timedelta(minutes=5) or dt < now - timedelta(days=7):
        return now
    return dt


# ── Housekeeping ──────────────────────────────────────────────────────────────
def sweep_stale_clip_uploads():
    """
    Called periodically (see media_cleanup.py). A camera that lost power or
    signal mid-upload may never come back for its clip; its half-finished
    segments would otherwise sit on disk forever.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.CLIP_STALE_HOURS)
    db = SessionLocal()
    try:
        stale = db.query(ClipUpload).filter(
            ClipUpload.status.in_([ClipUploadStatus.uploading, ClipUploadStatus.failed]),
            ClipUpload.updated_at < cutoff,
        ).all()
        for row in stale:
            remove_clip_dir(row.vehicle_id, row.client_clip_id)
            row.status = ClipUploadStatus.aborted
        if stale:
            db.commit()
            logger.info(f"Clip sweep — aborted {len(stale)} stale upload(s)")
    except Exception as e:
        db.rollback()
        logger.error(f"Clip sweep failed: {e}")
    finally:
        db.close()