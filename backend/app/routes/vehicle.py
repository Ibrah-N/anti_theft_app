from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertCategory, AlertSeverity

from app.core.dependencies import get_current_user, get_current_vehicle
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.mqtt_service import mqtt_service

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
    if not mqtt_service.is_connected:
        raise HTTPException(status_code=503, detail="Device not connected")

    mqtt_service.publish_fuel_command(vehicle.device_id, payload.state)

    return {
        "message": f"Fuel command sent to device",
        "state":   payload.state,
        "device":  vehicle.device_id,
    }