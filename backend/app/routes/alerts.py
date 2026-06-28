# app/routes/alerts.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.alert import Alert, AlertCategory
from app.models.vehicle import Vehicle
from app.models.user import User
from app.routes.vehicle import get_mock_user, get_user_vehicle
from app.schemas.alert import AlertResponse, AlertListResponse

router = APIRouter()

# ── List alerts ───────────────────────────────────────────────────────────────
@router.get("/", response_model=AlertListResponse)
def list_alerts(
    category: AlertCategory | None = Query(default=None),
    unread_only: bool              = Query(default=False),
    limit: int                     = Query(default=20, le=100),
    offset: int                    = Query(default=0),
    db: Session                    = Depends(get_db),
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    # Base query — always scoped to this vehicle
    query = db.query(Alert).filter(Alert.vehicle_id == vehicle.id)

    # Optional filters
    if category:
        query = query.filter(Alert.category == category)
    if unread_only:
        query = query.filter(Alert.is_read == False)

    # Total and unread counts before pagination
    total        = query.count()
    unread_count = db.query(Alert).filter(
        Alert.vehicle_id == vehicle.id,
        Alert.is_read    == False,
    ).count()

    # Paginated results — newest first
    alerts = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit).all()

    return AlertListResponse(
        total        = total,
        unread_count = unread_count,
        alerts       = alerts,
    )

# ── Mark single alert as read ─────────────────────────────────────────────────
@router.patch("/{alert_id}/read", response_model=AlertResponse)
def mark_read(
    alert_id: int,
    db: Session = Depends(get_db),
):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    alert = db.query(Alert).filter(
        Alert.id         == alert_id,
        Alert.vehicle_id == vehicle.id,   # security — can't read other vehicles' alerts
    ).first()

    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert

# ── Mark all alerts as read ───────────────────────────────────────────────────
@router.patch("/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db)):
    user    = get_mock_user(db)
    vehicle = get_user_vehicle(db, user)

    updated = db.query(Alert).filter(
        Alert.vehicle_id == vehicle.id,
        Alert.is_read    == False,
    ).update({"is_read": True})

    db.commit()
    return {"marked_read": updated}