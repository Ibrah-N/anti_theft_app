# app/services/mqtt_handlers.py

import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertCategory, AlertSeverity
from app.models.gps_reading import GPSReading

import asyncio
from app.services.websocket_service import ws_manager


logger = logging.getLogger(__name__)

# Set by app.main on startup — the FastAPI/uvicorn event loop that owns all WebSocket connections
main_event_loop: asyncio.AbstractEventLoop | None = None


def _broadcast_threadsafe(coro):
    """Schedule a broadcast coroutine on the main event loop from this MQTT thread."""
    if main_event_loop is None:
        logger.error("main_event_loop not set — cannot broadcast")
        return
    asyncio.run_coroutine_threadsafe(coro, main_event_loop)



def handle_mqtt_message(msg_type: str, device_id: str, data: dict):
    """
    Called by MQTTService._on_message for every incoming message.
    Opens its own DB session since this runs in a background thread.
    """
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(
            Vehicle.device_id == device_id
        ).first()

        if not vehicle:
            logger.warning(f"Unknown device_id: {device_id} — ignoring message")
            return

        if msg_type == "sensors":
            _handle_sensors(db, vehicle, data)
        elif msg_type == "gps":
            _handle_gps(db, vehicle, data)
        elif msg_type == "status":
            _handle_status(db, vehicle, data)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"DB error handling MQTT message: {e}")
    finally:
        db.close()


# ── Sensor handler ────────────────────────────────────────────────────────────
def _handle_sensors(db, vehicle, data: dict):
    """
    Expected payload:
    {
        "zone_fl": true, "zone_fr": true, "zone_rl": true,
        "zone_rr": true, "zone_bonnet": true, "zone_trunk": false
    }
    """
    zone_map = {
        "zone_fl":     "zone_fl",
        "zone_fr":     "zone_fr",
        "zone_rl":     "zone_rl",
        "zone_rr":     "zone_rr",
        "zone_bonnet": "zone_bonnet",
        "zone_trunk":  "zone_trunk",
    }

    zone_labels = {
        "zone_fl":     "Front Left Door",
        "zone_fr":     "Front Right Door",
        "zone_rl":     "Rear Left Door",
        "zone_rr":     "Rear Right Door",
        "zone_bonnet": "Bonnet",
        "zone_trunk":  "Trunk",
    }

    for key, attr in zone_map.items():
        if key not in data:
            continue

        new_state    = bool(data[key])
        current_state = getattr(vehicle, attr)

        # Update zone state
        setattr(vehicle, attr, new_state)

        # Zone just opened — create alert
        if current_state and not new_state:
            label = zone_labels[key]
            alert = Alert(
                vehicle_id  = vehicle.id,
                title       = f"{label} Opened",
                description = f"{label} opened unexpectedly",
                category    = AlertCategory.door,
                severity    = AlertSeverity.warning,
            )
            db.add(alert)
            db.flush()  # assigns alert.id and created_at before broadcasting
            logger.info(f"Alert created: {label} opened — vehicle {vehicle.id}")
            _broadcast_threadsafe(_broadcast_alert(vehicle, alert))

    logger.info(f"Sensor update saved — vehicle {vehicle.id}")
    
    # ── Push to WebSocket clients ─────────────────────────────────────────────
    _broadcast_threadsafe(_broadcast_sensors(vehicle))



async def _broadcast_sensors(vehicle):
    await ws_manager.broadcast(vehicle.id, {
        "type": "sensor_update",
        "payload": {
            "zone_fl":     vehicle.zone_fl,
            "zone_fr":     vehicle.zone_fr,
            "zone_rl":     vehicle.zone_rl,
            "zone_rr":     vehicle.zone_rr,
            "zone_bonnet": vehicle.zone_bonnet,
            "zone_trunk":  vehicle.zone_trunk,
        }
    })




# ── GPS handler ───────────────────────────────────────────────────────────────
def _handle_gps(db, vehicle, data: dict):
    """
    Expected payload:
    {
        "latitude": 33.6844, "longitude": 73.0479,
        "speed_kmh": 42.5, "city": "Islamabad", "address": "F-8 Markaz"
    }
    """
    reading = GPSReading(
        vehicle_id  = vehicle.id,
        latitude    = data.get("latitude",  0.0),
        longitude   = data.get("longitude", 0.0),
        speed_kmh   = data.get("speed_kmh", 0.0),
        city        = data.get("city"),
        address     = data.get("address"),
    )
    db.add(reading)

    # Keep vehicle live speed in sync
    vehicle.speed_kmh = data.get("speed_kmh", 0.0)

    logger.info(
        f"GPS reading saved — vehicle {vehicle.id} "
        f"lat={reading.latitude} lng={reading.longitude}"
    )


# ── Status handler ────────────────────────────────────────────────────────────
def _handle_status(db, vehicle, data: dict):
    """
    Expected payload:
    {
        "battery_level": 12.6, "signal_bars": 3,
        "engine_on": false, "fuel_flowing": true
    }
    """
    if "battery_level" in data:
        vehicle.battery_level = float(data["battery_level"])
    if "signal_bars" in data:
        vehicle.signal_bars   = int(data["signal_bars"])
    if "engine_on" in data:
        vehicle.engine_on     = bool(data["engine_on"])
    if "fuel_flowing" in data:
        vehicle.fuel_flowing  = bool(data["fuel_flowing"])

    logger.info(f"Status update saved — vehicle {vehicle.id}")

    # ── Push to WebSocket clients ─────────────────────────────────────────────
    _broadcast_threadsafe(_broadcast_status(vehicle))


async def _broadcast_status(vehicle):
    await ws_manager.broadcast(vehicle.id, {
        "type": "status_update",
        "payload": {
            "battery_level": vehicle.battery_level,
            "signal_bars":   vehicle.signal_bars,
            "engine_on":     vehicle.engine_on,
            "fuel_flowing":  vehicle.fuel_flowing,
            "speed_kmh":     vehicle.speed_kmh,
        }
    })


async def _broadcast_alert(vehicle, alert):
    created_at = alert.created_at or datetime.now(timezone.utc)
    await ws_manager.broadcast(vehicle.id, {
        "type": "alert",
        "payload": {
            "id":          alert.id,
            "title":       alert.title,
            "description": alert.description,
            "category":    alert.category.value,
            "severity":    alert.severity.value,
            "is_read":     alert.is_read,
            "created_at":  created_at.isoformat(),
        }
    })