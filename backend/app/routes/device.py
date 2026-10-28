# app/routes/device.py
#
# Endpoints used by the camera / firmware to put EVENT clips into the same
# gallery the app already shows. Mounted at /api/device.
#
#   POST   /key                                  (owner, JWT)  create / rotate the device key
#   POST   /clips                                (device key)  announce a clip (safe to repeat)
#   GET    /clips/{clip_id}                      (device key)  which segments does the server have?
#   PUT    /clips/{clip_id}/segments/{index}     (device key)  upload one piece (safe to repeat)
#   POST   /clips/{clip_id}/finish               (device key)  join pieces -> gallery item
#   DELETE /clips/{clip_id}                      (device key)  give up on this clip
#
# Everything is idempotent on purpose: on a cellular link a request can be cut
# off after the server already acted on it, so the camera must be able to
# repeat any call without creating duplicates.

import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi import Path as PathParam
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_vehicle
from app.core.device_auth import generate_device_key, hash_device_key, get_device_vehicle
from app.models.camera_media import CameraMedia, CameraMediaType, CameraMediaSource
from app.models.clip_upload import ClipUpload, ClipUploadStatus
from app.models.vehicle import Vehicle
from app.schemas.camera_media import CameraMediaResponse
from app.schemas.clip_upload import (
    DeviceKeyResponse, ClipStartRequest, ClipFinishRequest, ClipStatusResponse,
)
from app.services import clip_storage
from app.services.mqtt_handlers import notify_clip_ready
from app.services.clip_storage import CLIP_ID_PATTERN, ClipJoinError

logger = logging.getLogger(__name__)
router = APIRouter()

ClipId = Annotated[str, PathParam(pattern=CLIP_ID_PATTERN, min_length=8, max_length=64)]
SegIndex = Annotated[int, PathParam(ge=0)]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_upload(db: Session, vehicle: Vehicle, clip_id: str, lock: bool = False) -> ClipUpload:
    q = db.query(ClipUpload).filter(
        ClipUpload.vehicle_id == vehicle.id,      # a device can only ever touch its own vehicle's clips
        ClipUpload.client_clip_id == clip_id,
    )
    if lock:
        q = q.with_for_update()                   # serialise two simultaneous "finish" calls
    upload = q.first()
    if upload is None:
        raise HTTPException(status_code=404, detail="Unknown clip — call POST /clips first")
    return upload


def _status(db: Session, vehicle: Vehicle, upload: ClipUpload) -> ClipStatusResponse:
    segs: dict[int, int] = {}
    if upload.status in (ClipUploadStatus.uploading, ClipUploadStatus.failed):
        segs = clip_storage.list_segments(vehicle.id, upload.client_clip_id)

    media = db.get(CameraMedia, upload.media_id) if upload.media_id else None
    return ClipStatusResponse(
        client_clip_id    = upload.client_clip_id,
        status            = upload.status,
        segments_received = sorted(segs),
        bytes_received    = sum(segs.values()) if segs else upload.bytes_received,
        total_segments    = upload.total_segments,
        media_id          = upload.media_id,
        media             = CameraMediaResponse.model_validate(media) if media else None,
    )


# ── Owner: create / rotate the device key ─────────────────────────────────────
@router.post("/key", response_model=DeviceKeyResponse)
def create_device_key(
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    """
    Called by the vehicle's OWNER (normal app login). Returns the key once;
    only its hash is stored. Calling this again replaces the key, which
    immediately stops the old one from working — use it if a key leaks.
    """
    key = generate_device_key()
    vehicle.device_key_hash       = hash_device_key(key)
    vehicle.device_key_created_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Device key (re)created — vehicle {vehicle.id}")
    return DeviceKeyResponse(device_id=vehicle.device_id, device_key=key)


# ── Camera: announce a clip ───────────────────────────────────────────────────
@router.post("/clips", response_model=ClipStatusResponse)
def start_clip(
    payload: ClipStartRequest,
    vehicle: Vehicle = Depends(get_device_vehicle),
    db: Session = Depends(get_db),
):
    upload = db.query(ClipUpload).filter(
        ClipUpload.vehicle_id == vehicle.id,
        ClipUpload.client_clip_id == payload.client_clip_id,
    ).first()

    if upload is None:
        upload = ClipUpload(
            vehicle_id     = vehicle.id,
            client_clip_id = payload.client_clip_id,
            trigger_reason = payload.trigger_reason,
            recorded_at    = clip_storage.sane_time(payload.recorded_at),
        )
        db.add(upload)
        try:
            db.commit()
        except IntegrityError:                    # two identical requests raced — the other one won
            db.rollback()
            upload = _get_upload(db, vehicle, payload.client_clip_id)
        else:
            db.refresh(upload)
            logger.info(f"Clip started — vehicle {vehicle.id} clip={upload.client_clip_id} "
                        f"reason={upload.trigger_reason}")
    elif upload.status == ClipUploadStatus.aborted:
        # The camera is starting this clip over: forget the old attempt.
        clip_storage.remove_clip_dir(vehicle.id, upload.client_clip_id)
        upload.status         = ClipUploadStatus.uploading
        upload.bytes_received = 0
        upload.total_segments = None
        db.commit()

    return _status(db, vehicle, upload)


@router.get("/clips/{clip_id}", response_model=ClipStatusResponse)
def clip_status(
    clip_id: ClipId,
    vehicle: Vehicle = Depends(get_device_vehicle),
    db: Session = Depends(get_db),
):
    return _status(db, vehicle, _get_upload(db, vehicle, clip_id))


# ── Camera: upload one segment ────────────────────────────────────────────────
@router.put("/clips/{clip_id}/segments/{index}", response_model=ClipStatusResponse)
async def upload_segment(
    clip_id: ClipId,
    index: SegIndex,
    request: Request,
    x_segment_sha256: str | None = Header(default=None),
    vehicle: Vehicle = Depends(get_device_vehicle),
    db: Session = Depends(get_db),
):
    """
    Body = the raw bytes of the segment (Content-Type: application/octet-stream).
    Optional header X-Segment-SHA256: hex digest — if sent, the server verifies
    the piece arrived intact. Re-sending an index simply replaces it.
    """
    upload = _get_upload(db, vehicle, clip_id)

    if upload.status == ClipUploadStatus.complete:
        return _status(db, vehicle, upload)       # already in the gallery — nothing to do
    if upload.status == ClipUploadStatus.aborted:
        raise HTTPException(status_code=409, detail="Clip was aborted — call POST /clips to start over")
    if index >= settings.CLIP_MAX_SEGMENTS:
        raise HTTPException(status_code=422, detail=f"Segment index must be below {settings.CLIP_MAX_SEGMENTS}")

    clip_storage.check_disk_space()
    clip_storage.clip_dir(vehicle.id, clip_id, create=True)
    final = clip_storage.segment_path(vehicle.id, clip_id, index)
    part  = final.with_suffix(".part")

    other_bytes = sum(size for i, size in clip_storage.list_segments(vehicle.id, clip_id).items() if i != index)

    # Stream to disk with hard caps — never trust the client-declared size.
    size = 0
    digest = hashlib.sha256()
    try:
        with open(part, "wb") as out:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > settings.CLIP_MAX_SEGMENT_BYTES:
                    raise HTTPException(status_code=413, detail="Segment too large")
                if other_bytes + size > settings.MEDIA_MAX_RECORDING_BYTES:
                    raise HTTPException(status_code=413, detail="Clip exceeds the maximum recording size")
                digest.update(chunk)
                out.write(chunk)
    except HTTPException:
        part.unlink(missing_ok=True)
        raise
    except Exception as e:                        # includes the client disconnecting mid-upload
        part.unlink(missing_ok=True)
        logger.info(f"Segment upload interrupted — vehicle {vehicle.id} clip={clip_id} seg={index}: {e!r}")
        raise HTTPException(status_code=400, detail="Upload interrupted — resend this segment")

    if size == 0:
        part.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Empty segment")

    if x_segment_sha256 and x_segment_sha256.strip().lower() != digest.hexdigest():
        part.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Checksum mismatch — resend this segment")

    os.replace(part, final)                       # atomic: a segment is either complete or absent

    upload.bytes_received = other_bytes + size
    db.commit()
    return _status(db, vehicle, upload)


# ── Camera: finish -> join -> gallery ─────────────────────────────────────────
@router.post("/clips/{clip_id}/finish", response_model=ClipStatusResponse)
def finish_clip(
    clip_id: ClipId,
    payload: ClipFinishRequest,
    background: BackgroundTasks,
    vehicle: Vehicle = Depends(get_device_vehicle),,
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, vehicle, clip_id, lock=True)

    if upload.status == ClipUploadStatus.complete:
        return _status(db, vehicle, upload)       # repeat call — same answer, no second gallery item
    if upload.status == ClipUploadStatus.aborted:
        raise HTTPException(status_code=409, detail="Clip was aborted — call POST /clips to start over")
    if payload.total_segments > settings.CLIP_MAX_SEGMENTS:
        raise HTTPException(status_code=422, detail=f"At most {settings.CLIP_MAX_SEGMENTS} segments per clip")

    present = clip_storage.list_segments(vehicle.id, clip_id)
    missing = [i for i in range(payload.total_segments) if i not in present]

    if missing and not payload.allow_partial:
        # Tell the camera exactly what to resend, then call finish again.
        raise HTTPException(status_code=409, detail={"error": "missing_segments", "missing": missing})

    use_indexes = [i for i in range(payload.total_segments) if i in present]
    if not use_indexes:
        raise HTTPException(status_code=422, detail="No segments received")

    clip_storage.check_disk_space()
    upload.total_segments = payload.total_segments
    joined = clip_storage.clip_dir(vehicle.id, clip_id) / "joined.mp4"

    try:
        clip_storage.join_segments(
            [clip_storage.segment_path(vehicle.id, clip_id, i) for i in use_indexes], joined,
        )
    except ClipJoinError as e:
        logger.error(f"Clip join failed — vehicle {vehicle.id} clip={clip_id}: {e}")
        upload.status = ClipUploadStatus.failed
        db.commit()
        raise HTTPException(status_code=500, detail="Could not join the segments into a video")

    final_size = joined.stat().st_size
    if final_size > settings.MEDIA_MAX_RECORDING_BYTES:
        joined.unlink(missing_ok=True)
        upload.status = ClipUploadStatus.failed
        db.commit()
        raise HTTPException(status_code=413, detail="Joined clip exceeds the maximum recording size")

    duration = clip_storage.probe_duration(joined) or payload.duration_seconds
    dest = clip_storage.media_dir(vehicle.id) / f"{uuid.uuid4().hex}.mp4"
    shutil.move(str(joined), str(dest))           # also works if the two folders are on different disks

    existing_count = db.query(CameraMedia).filter(
        CameraMedia.vehicle_id == vehicle.id,
        CameraMedia.media_type == CameraMediaType.recording,
    ).count()

    media = CameraMedia(
        vehicle_id       = vehicle.id,
        sequence_number  = existing_count + 1,
        media_type       = CameraMediaType.recording,
        file_path        = str(dest),
        file_size_bytes  = final_size,
        duration_seconds = duration,
        source           = CameraMediaSource.event,
        trigger_reason   = upload.trigger_reason,
        client_clip_id   = upload.client_clip_id,
        # Sort and expire by when it HAPPENED, not when the upload finished.
        created_at       = upload.recorded_at or datetime.now(timezone.utc),
    )
    db.add(media)
    db.flush()

    upload.media_id = media.id
    upload.status   = ClipUploadStatus.complete
    db.commit()
    db.refresh(upload)

    clip_storage.remove_clip_dir(vehicle.id, clip_id)
    # Tell the app (WebSocket) and the owner (push) — after the response is sent,
    # and only on the first successful finish (repeats returned earlier).
    background.add_task(notify_clip_ready, vehicle.id, {
        "media_id":         media.id,
        "source":           "event",
        "trigger_reason":   media.trigger_reason,
        "duration_seconds": media.duration_seconds,
        "created_at":       media.created_at.isoformat() if media.created_at else None,
    })
    logger.info(f"Clip complete — vehicle {vehicle.id} clip={clip_id} media_id={media.id} "
                f"segments={len(use_indexes)}/{payload.total_segments} size={final_size}")
    return _status(db, vehicle, upload)


# ── Camera: give up ───────────────────────────────────────────────────────────
@router.delete("/clips/{clip_id}", response_model=ClipStatusResponse)
def abort_clip(
    clip_id: ClipId,
    vehicle: Vehicle = Depends(get_device_vehicle),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, vehicle, clip_id, lock=True)
    if upload.status == ClipUploadStatus.complete:
        raise HTTPException(status_code=409, detail="Clip is already in the gallery — delete it from the app")
    clip_storage.remove_clip_dir(vehicle.id, clip_id)
    upload.status = ClipUploadStatus.aborted
    db.commit()
    return _status(db, vehicle, upload)