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