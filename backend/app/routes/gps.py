# app/routes/gps.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.gps_reading import GPSReading
from app.core.dependencies import get_current_vehicle
from app.models.vehicle import Vehicle
from app.schemas.gps import GPSReadingCreate, GPSReadingResponse, GPSHistoryResponse

router = APIRouter()

# ── Latest known location ─────────────────────────────────────────────────────
@router.get("/latest", response_model=GPSReadingResponse)
def get_latest(
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db)
):

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
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):

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
    vehicle: Vehicle = Depends(get_current_vehicle),
    db: Session = Depends(get_db),
):
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

# ── Request live GPS from device ──────────────────────────────────────────────
@router.post("/request", response_model=dict)
def request_gps(
    vehicle: Vehicle = Depends(get_current_vehicle),
):
    from app.services.mqtt_service import mqtt_service
    if not mqtt_service.is_connected:
        raise HTTPException(
            status_code=503,
            detail="MQTT broker not connected"
        )
    mqtt_service.publish_gps_request(vehicle.device_id)
    return {
        "message": "GPS request sent to device",
        "device_id": vehicle.device_id,
    }