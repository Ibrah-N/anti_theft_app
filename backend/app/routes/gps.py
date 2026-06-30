# app/routes/gps.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.gps_reading import GPSReading
from app.routes.vehicle import get_mock_user, get_user_vehicle
from app.schemas.gps import GPSReadingCreate, GPSReadingResponse, GPSHistoryResponse

router = APIRouter()

# ── Latest known location ─────────────────────────────────────────────────────
@router.get("/latest", response_model=GPSReadingResponse)
def get_latest(db: Session = Depends(get_db)):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    latest = (
        db.query(GPSReading)
        .filter(GPSReading.vehicle_id == vehicle.id)
        .order_by(desc(GPSReading.recorded_at))
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail="No GPS readings yet for this vehicle")

    return latest

# ── History ────────────────────────────────────────────────────────────────────
@router.get("/history", response_model=GPSHistoryResponse)
def get_history(
    limit: int  = Query(default=50, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    query = db.query(GPSReading).filter(GPSReading.vehicle_id == vehicle.id)

    total    = query.count()
    readings = (
        query.order_by(desc(GPSReading.recorded_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return GPSHistoryResponse(total=total, readings=readings)

# ── Manual insert — Phase 3 replaces this with MQTT-driven inserts ───────────
@router.post("/", response_model=GPSReadingResponse, status_code=201)
def record_reading(
    payload: GPSReadingCreate,
    db: Session = Depends(get_db),
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    reading = GPSReading(
        vehicle_id = vehicle.id,
        latitude   = payload.latitude,
        longitude  = payload.longitude,
        speed_kmh  = payload.speed_kmh,
        city       = payload.city,
        address    = payload.address,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Keep vehicle's live speed in sync
    vehicle.speed_kmh = payload.speed_kmh
    db.commit()

    return reading