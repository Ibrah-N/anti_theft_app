from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ── Zone states ───────────────────────────────────────────────────────────────
class ZoneStates(BaseModel):
    zone_fl:     bool
    zone_fr:     bool
    zone_rl:     bool
    zone_rr:     bool
    zone_bonnet: bool
    zone_trunk:  bool

# ── Vehicle response ──────────────────────────────────────────────────────────
class VehicleResponse(BaseModel):
    id:            int
    name:          str
    reg_number:    str
    device_id:     str
    engine_on:     bool
    fuel_flowing:  bool
    speed_kmh:     float
    battery_level: float
    signal_bars:   int
    zone_fl:       bool
    zone_fr:       bool
    zone_rl:       bool
    zone_rr:       bool
    zone_bonnet:   bool
    zone_trunk:    bool
    is_armed:       bool
    doors_locked:   bool
    mirror_fl:      bool
    mirror_fr:      bool
    mirror_rl:      bool
    mirror_rr:      bool
    engine_started: bool
    ac_on:          bool
    updated_at:    datetime

    model_config = {"from_attributes": True}

# ── Register vehicle ──────────────────────────────────────────────────────────
class VehicleRegister(BaseModel):
    name:       str
    reg_number: str
    device_id:  str

# ── Command payload ───────────────────────────────────────────────────────────
class CommandPayload(BaseModel):
    state: bool   # True = ON/FLOW, False = OFF/CUT

# ── Device ACK payload (sg/{device_id}/ack) ──────────────────────────────────
class AckPayload(BaseModel):
    cmd:     str    # e.g. "lock", "mirror_fl", "start", "ac", "arm"
    state:   bool
    success: bool