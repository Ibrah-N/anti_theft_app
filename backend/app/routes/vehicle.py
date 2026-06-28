from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertCategory, AlertSeverity
from app.models.user import User
from app.schemas.vehicle import VehicleResponse, VehicleRegister, CommandPayload

router = APIRouter()

# ── Temporary auth helper — replaced by real JWT in Step 3 ───────────────────
def get_mock_user(db: Session) -> User:
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user found — register first"
        )
    return user

def get_user_vehicle(db: Session, user: User) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.owner_id == user.id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vehicle registered for this user"
        )
    return vehicle

# ── Register vehicle ──────────────────────────────────────────────────────────
@router.post("/register", response_model=VehicleResponse, status_code=201)
def register_vehicle(
    payload: VehicleRegister,
    db: Session = Depends(get_db)
):
    user = get_mock_user(db)

    # Check device_id not already taken
    existing = db.query(Vehicle).filter(
        Vehicle.device_id == payload.device_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Device ID already registered"
        )

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
def get_status(db: Session = Depends(get_db)):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)
    return vehicle

# ── Engine control ────────────────────────────────────────────────────────────
@router.post("/engine", response_model=VehicleResponse)
def control_engine(
    payload: CommandPayload,
    db: Session = Depends(get_db)
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    vehicle.engine_on = payload.state
    db.commit()
    db.refresh(vehicle)

    # Log alert when engine is turned off remotely
    if not payload.state:
        alert = Alert(
            vehicle_id  = vehicle.id,
            title       = "Engine disabled remotely",
            description = "Engine cutoff triggered via SmartGuard app",
            category    = AlertCategory.engine,
            severity    = AlertSeverity.warning,
        )
        db.add(alert)
        db.commit()

    # TODO Phase 3: publish MQTT command to device
    return vehicle

# ── Fuel control ──────────────────────────────────────────────────────────────
@router.post("/fuel", response_model=VehicleResponse)
def control_fuel(
    payload: CommandPayload,
    db: Session = Depends(get_db)
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    vehicle.fuel_flowing = payload.state
    db.commit()
    db.refresh(vehicle)

    # Log alert when fuel is cut remotely
    if not payload.state:
        alert = Alert(
            vehicle_id  = vehicle.id,
            title       = "Fuel cutoff activated",
            description = "Fuel supply cut via SmartGuard app",
            category    = AlertCategory.engine,
            severity    = AlertSeverity.warning,
        )
        db.add(alert)
        db.commit()

    # TODO Phase 3: publish MQTT command to device
    return vehicle