# app/routes/ws.py

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.websocket_service import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_vehicle_from_token(token: str) -> Vehicle | None:
    """Validate JWT and return vehicle — used inside WebSocket handshake."""
    db = SessionLocal()
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None

        vehicle = db.query(Vehicle).filter(
            Vehicle.owner_id == user.id
        ).first()
        return vehicle
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),   # ws://localhost:8000/ws?token=eyJ...
):
    # ── Auth ──────────────────────────────────────────────────────────────────
    vehicle = get_vehicle_from_token(token)
    if not vehicle:
        await websocket.close(code=4001)
        logger.warning("WebSocket rejected — invalid token")
        return

    vehicle_id = vehicle.id
    logger.info(f"WebSocket authenticated — vehicle {vehicle_id}")

    # ── Connect ───────────────────────────────────────────────────────────────
    await ws_manager.connect(vehicle_id, websocket)

    # ── Send initial state immediately on connect ─────────────────────────────
    await websocket.send_json({
        "type":    "initial_state",
        "payload": {
            "engine_on":     vehicle.engine_on,
            "fuel_flowing":  vehicle.fuel_flowing,
            "battery_level": vehicle.battery_level,
            "signal_bars":   vehicle.signal_bars,
            "speed_kmh":     vehicle.speed_kmh,
            "zone_fl":       vehicle.zone_fl,
            "zone_fr":       vehicle.zone_fr,
            "zone_rl":       vehicle.zone_rl,
            "zone_rr":       vehicle.zone_rr,
            "zone_bonnet":   vehicle.zone_bonnet,
            "zone_trunk":    vehicle.zone_trunk,
        }
    })

    # ── Keep alive — wait for disconnect ──────────────────────────────────────
    try:
        while True:
            # We don't expect messages from client
            # but we must await to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(vehicle_id, websocket)
        logger.info(f"WebSocket disconnected — vehicle {vehicle_id}")