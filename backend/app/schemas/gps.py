# app/schemas/gps.py

from datetime import datetime

from pydantic import BaseModel


# ── Incoming reading (from device, used in Phase 3 MQTT bridge) ──────────────
class GPSReadingCreate(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    city: str | None = None
    address: str | None = None


# ── Response ──────────────────────────────────────────────────────────────────
class GPSReadingResponse(BaseModel):
    id: int
    vehicle_id: int
    latitude: float
    longitude: float
    speed_kmh: float
    city: str | None
    address: str | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ── History list response ─────────────────────────────────────────────────────
class GPSHistoryResponse(BaseModel):
    total: int
    readings: list[GPSReadingResponse]
