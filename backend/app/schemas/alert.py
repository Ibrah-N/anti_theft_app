from pydantic import BaseModel
from datetime import datetime
from app.models.alert import AlertCategory, AlertSeverity

# ── Alert response ────────────────────────────────────────────────────────────
class AlertResponse(BaseModel):
    id:          int
    vehicle_id:  int
    title:       str
    description: str
    category:    AlertCategory
    severity:    AlertSeverity
    is_read:     bool
    created_at:  datetime

    model_config = {"from_attributes": True}

# ── List response with unread count ──────────────────────────────────────────
class AlertListResponse(BaseModel):
    total:        int
    unread_count: int
    alerts:       list[AlertResponse]