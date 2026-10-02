from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertCategory, AlertSeverity

from app.core.dependencies import get_current_user, get_current_vehicle
from app.models.user import User
from app.models.vehicle import Vehicle

from app.services.mqtt_service import mqtt_service
from app.services import webrtc_signaling
from app.services import turn_credentials

import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
from app.core.config import settings
from app.models.camera_media import CameraMedia, CameraMediaType
from app.schemas.camera_media import CameraMediaResponse, CameraMediaListResponse

from app.schemas.vehicle import VehicleResponse, VehicleRegister, CommandPayload

router = APIRouter()






# ── Register vehicle ──────────────────────────────────────────────────────────
@router.post("/register", response_model=VehicleResponse, status_code=201)
def register_vehicle(
    payload: VehicleRegister,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Vehicle).filter(Vehicle.device_id == payload.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device ID already registered")

    vehicle = Vehicle(
        owner_id   = user.id,
        name       = payload.name,
        reg_number = payload.reg_number,
        device_id  = payload.device_id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── Get vehicle status ────────────────────────────────────────────────────────
@router.get("/status", response_model=VehicleResponse)
def get_status(vehicle: Vehicle = Depends(get_current_vehicle)):
    return vehicle

# ── Engine control ────────────────────────────────────────────────────────────
@router.post("/engine", response_model=dict)
def control_engine(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not vehicle.is_armed:
        raise HTTPException(
            status_code=409,
            detail="Vehicle is disarmed — arm it to use this control",
        )
        
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    # Publish command to device — don't save to DB yet
    mqtt_service.publish_engine_command(vehicle.device_id, payload.state)

    return {
        "message": f"Engine command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Fuel control ──────────────────────────────────────────────────────────────
@router.post("/fuel", response_model=dict)
def control_fuel(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not vehicle.is_armed:
        raise HTTPException(
            status_code=409,
            detail="Vehicle is disarmed — arm it to use this control",
        )

    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    mqtt_service.publish_fuel_command(vehicle.device_id, payload.state)

    return {
        "message": f"Fuel command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Door lock control ─────────────────────────────────────────────────────────
@router.post("/lock", response_model=dict)
def control_lock(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    # DB is NOT updated here — only once the device ACK confirms success
    mqtt_service.publish_lock_command(vehicle.device_id, payload.state)

    return {
        "message": "Lock command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Mirror control ─────────────────────────────────────────────────────────────
@router.post("/mirror/{position}", response_model=dict)
def control_mirror(
    position: Literal["fl", "fr", "rl", "rr"],
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    # payload.state: True = fold, False = unfold
    mqtt_service.publish_mirror_command(vehicle.device_id, position, payload.state)

    return {
        "message": f"Mirror {position} command sent to device",
        "position": position,
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Engine start (starter motor) control ───────────────────────────────────────
@router.post("/start", response_model=dict)
def control_start(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not vehicle.is_armed:
        raise HTTPException(
            status_code=409,
            detail="Vehicle is disarmed — arm it to use this control",
        )

    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    mqtt_service.publish_start_command(vehicle.device_id, payload.state)

    return {
        "message": "Start command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── AC control ──────────────────────────────────────────────────────────────────
@router.post("/ac", response_model=dict)
def control_ac(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):

    if not vehicle.is_armed:
        raise HTTPException(
            status_code=409,
            detail="Vehicle is disarmed — arm it to use this control",
        )

    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    mqtt_service.publish_ac_command(vehicle.device_id, payload.state)

    return {
        "message": "AC command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Arm / disarm control ─────────────────────────────────────────────────────────
@router.post("/arm", response_model=dict)
def control_arm(
    payload: CommandPayload,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    mqtt_service.publish_arm_command(vehicle.device_id, payload.state)

    return {
        "message": "Arm command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }


# ── Camera / WebRTC signaling ─────────────────────────────────────────────────
# NOTE: not gated on is_armed, unlike engine/fuel/ac/start — checking your own
# camera while parked and disarmed is a reasonable thing to want. Flip this by
# adding the same 4-line `if not vehicle.is_armed: raise HTTPException(...)`
# block used in the other control routes, if you'd rather it require armed.
@router.post("/camera/start", response_model=dict)
def start_camera(
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    call_id = webrtc_signaling.start_session(vehicle.id)
    mqtt_service.publish_camera_start_command(vehicle.device_id, call_id)

    return {
        "message":     "Camera start command sent to device",
        "call_id":     call_id,
        "device":      vehicle.device_id,
        "ice_servers": turn_credentials.get_ice_servers(),
    }


@router.get("/camera/ice-servers", response_model=dict)
def get_ice_servers(
    vehicle: Vehicle = Depends(get_current_vehicle),
):
    """
    Standalone endpoint for refreshing ICE servers independently of starting
    a new session — e.g. if a long call needs fresh (non-expired) TURN
    credentials mid-stream without tearing down the whole call_id.
    """
    return {"ice_servers": turn_credentials.get_ice_servers()}


@router.post("/camera/stop", response_model=dict)
def stop_camera(
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    call_id = webrtc_signaling.get_call_id(vehicle.id)
    if call_id and mqtt_service.is_connected:
        mqtt_service.publish_camera_stop_command(vehicle.device_id, call_id)

        webrtc_signaling.end_session(vehicle.id)

    return {
        "message": "Camera stop command sent to device",
        "device":  vehicle.device_id,
    }


# ── Camera media (snapshots / recordings) ───────────────────────────────────────
# Video now goes straight from the camera to the app over WebRTC and never
# passes through this backend — so it can't grab frames itself the way it
# could with a server-relayed stream. Instead, whichever side is currently
# holding the video (the app today; the camera firmware later, once it
# exists) captures locally and uploads the finished file here. One generic
# store, usable by either side, keyed only by vehicle ownership.

def _media_dir(vehicle_id: int) -> Path:
    d = Path(settings.MEDIA_ROOT) / str(vehicle_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _check_disk_space():
    usage = shutil.disk_usage(settings.MEDIA_ROOT)
    if usage.free < settings.MEDIA_MIN_FREE_BYTES:
        raise HTTPException(
            status_code=507,  # Insufficient Storage
            detail="Server storage is critically low — try again later",
        )


@router.post("/camera/media", response_model=CameraMediaResponse)
async def upload_camera_media(
    media_type: CameraMediaType = Form(...),
    duration_seconds: float | None = Form(default=None),
    file: UploadFile = File(...),
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    _check_disk_space()

    max_bytes = (
        settings.MEDIA_MAX_SNAPSHOT_BYTES
        if media_type == CameraMediaType.snapshot
        else settings.MEDIA_MAX_RECORDING_BYTES
    )

    # Sanitize the extension rather than trust it outright — still only
    # ever used to name a file inside our own per-vehicle folder, never as
    # a path itself.
    ext = Path(file.filename or "").suffix or (
        ".png" if media_type == CameraMediaType.snapshot else ".mp4"
    )
    ext = "".join(c for c in ext if c.isalnum() or c == ".")[:10] or ".bin"
    dest_path = _media_dir(vehicle.id) / f"{uuid.uuid4().hex}{ext}"

    # Stream to disk in chunks with a hard byte-count cap, rather than
    # trusting the client-declared size — a spoofed Content-Length
    # shouldn't be able to fill the disk.
    size = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB "
                               f"limit for {media_type.value}",
                    )
                out.write(chunk)
    except HTTPException:
        dest_path.unlink(missing_ok=True)
        raise
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Upload failed")

    existing_count = db.query(CameraMedia).filter(
        CameraMedia.vehicle_id == vehicle.id,
        CameraMedia.media_type == media_type,
    ).count()

    media = CameraMedia(
        vehicle_id=vehicle.id,
        sequence_number=existing_count + 1,
        media_type=media_type,
        file_path=str(dest_path),
        file_size_bytes=size,
        duration_seconds=duration_seconds,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.get("/camera/media", response_model=CameraMediaListResponse)
def list_camera_media(
    media_type: CameraMediaType | None = None,
    limit: int = 20,
    offset: int = 0,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    query = db.query(CameraMedia).filter(CameraMedia.vehicle_id == vehicle.id)
    if media_type:
        query = query.filter(CameraMedia.media_type == media_type)

    total = query.count()
    items = (
        query.order_by(CameraMedia.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return CameraMediaListResponse(total=total, items=items)


@router.get("/camera/media/{media_id}/file")
def download_camera_media(
    media_id: int,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    media = db.query(CameraMedia).filter(
        CameraMedia.id == media_id,
        CameraMedia.vehicle_id == vehicle.id,  # ownership check, every time
    ).first()

    if not media or not os.path.exists(media.file_path):
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(media.file_path)


@router.delete("/camera/media/{media_id}", response_model=dict)
def delete_camera_media(
    media_id: int,
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
    media = db.query(CameraMedia).filter(
        CameraMedia.id == media_id,
        CameraMedia.vehicle_id == vehicle.id,
    ).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if os.path.exists(media.file_path):
        os.remove(media.file_path)

    db.delete(media)
    db.commit()
    return {"message": "Deleted"}