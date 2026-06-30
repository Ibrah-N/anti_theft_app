# app/schemas/gps.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ── Incoming reading (from device, used in Phase 3 MQTT bridge) ──────────────
class GPSReadingCreate(BaseModel):
    latitude:  float
    longitude: float
    speed_kmh: float = 0.0
    city:      Optional[str] = None
    address:   Optional[str] = None

# ── Response ──────────────────────────────────────────────────────────────────
class GPSReadingResponse(BaseModel):
    id:          int
    vehicle_id:  int
    latitude:    float
    longitude:   float
    speed_kmh:   float
    city:        Optional[str]
    address:     Optional[str]
    recorded_at: datetime

    model_config = {"from_attributes": True}

# ── History list response ─────────────────────────────────────────────────────
class GPSHistoryResponse(BaseModel):
    total:    int
    readings: list[GPSReadingResponse]