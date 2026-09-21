# app/services/mqtt_handlers.py

import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertCategory, AlertSeverity
from app.models.gps_reading import GPSReading

import asyncio
from app.services.websocket_service import ws_manager

from firebase_admin import messaging
from app.models.device_token import DeviceToken

logger = logging.getLogger(__name__)

# Set by app.main on startup — the FastAPI/uvicorn event loop that owns all WebSocket connections
main_event_loop: asyncio.AbstractEventLoop | None = None


def _broadcast_threadsafe(coro):
    """Schedule a broadcast coroutine on the main event loop from this MQTT thread."""
    if main_event_loop is None:
        logger.error("main_event_loop not set — cannot broadcast")
        return
    asyncio.run_coroutine_threadsafe(coro, main_event_loop)


def _send_push_notification(db, vehicle, title: str, body: str):
    """Send an FCM push to every device registered to this vehicle's owner."""
    tokens = db.query(DeviceToken).filter(
        DeviceToken.user_id == vehicle.owner_id
    ).all()

    if not tokens:
        return

    for device in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="alerts_channel",
                        sound="default",
                    ),
                ),
                token=device.fcm_token,
            )
            messaging.send(message)
        except Exception as e:
            logger.error(f"FCM push failed for token {device.fcm_token[:20]}...: {e}")


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

        # ── Disarmed = sleep mode ────────────────────────────────────────────
        # When disarmed, the device is expected to sleep — no periodic sensor
        # or GPS publishing — to save power instead of running 24/7. This is
        # a backend-side safety net: if a stray sensors/gps message arrives
        # anyway while disarmed, we drop it here entirely (no DB write, no
        # WebSocket broadcast, no push notification).
        #
        # "status" is NOT gated here, because it's how the device tells us
        # about an arm-state change (e.g. a hardware key-fob toggle) — that
        # needs to reach the app even while disarmed. _handle_status applies
        # its own, narrower suppression: it still processes the message, but
        # only broadcasts to the app if the vehicle is armed OR the arm state
        # just changed. "ack" is never gated, since a pending command (most
        # importantly arm/disarm itself) must always be able to confirm.
        if msg_type in ("sensors", "gps") and not vehicle.is_armed:
            logger.info(
                f"Vehicle {vehicle.id} is disarmed — dropping '{msg_type}' "
                f"message (sleep mode, no data transfer)"
            )
            return

        if msg_type == "sensors":
            _handle_sensors(db, vehicle, data)
        elif msg_type == "gps":
            _handle_gps(db, vehicle, data)
        elif msg_type == "status":
            _handle_status(db, vehicle, data)
        elif msg_type == "ack":
            _handle_ack(db, vehicle, data)

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
            _send_push_notification(db, vehicle, alert.title, alert.description)

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
    was_armed = vehicle.is_armed

    if "battery_level" in data:
        vehicle.battery_level = float(data["battery_level"])
    if "signal_bars" in data:
        vehicle.signal_bars   = int(data["signal_bars"])
    if "engine_on" in data:
        vehicle.engine_on     = bool(data["engine_on"])
    if "fuel_flowing" in data:
        vehicle.fuel_flowing  = bool(data["fuel_flowing"])
    if "is_armed" in data:
        vehicle.is_armed      = bool(data["is_armed"])

    logger.info(f"Status update saved — vehicle {vehicle.id}")

    # ── Push to WebSocket clients ─────────────────────────────────────────────
    # While disarmed, the device is asleep and shouldn't be feeding the app
    # anything — except the arm-state transition itself, so the app's
    # ARM/DISARM button stays in sync even though everything else goes quiet.
    armed_state_changed = was_armed != vehicle.is_armed
    if vehicle.is_armed or armed_state_changed:
        _broadcast_threadsafe(_broadcast_status(vehicle))
    else:
        logger.info(
            f"Vehicle {vehicle.id} disarmed — suppressing status broadcast "
            f"(sleep mode, no data transfer)"
        )


async def _broadcast_status(vehicle):
    await ws_manager.broadcast(vehicle.id, {
        "type": "status_update",
        "payload": {
            "battery_level": vehicle.battery_level,
            "signal_bars":   vehicle.signal_bars,
            "engine_on":     vehicle.engine_on,
            "fuel_flowing":  vehicle.fuel_flowing,
            "speed_kmh":     vehicle.speed_kmh,
            "is_armed":      vehicle.is_armed,
        }
    })


# ── ACK handler ───────────────────────────────────────────────────────────────
# Maps the "cmd" field of an ACK payload to the Vehicle column it confirms.
_ACK_CMD_TO_ATTR = {
    "lock":       "doors_locked",
    "mirror_fl":  "mirror_fl",
    "mirror_fr":  "mirror_fr",
    "mirror_rl":  "mirror_rl",
    "mirror_rr":  "mirror_rr",
    "start":      "engine_started",
    "ac":         "ac_on",
    "arm":        "is_armed",
}


def _handle_ack(db, vehicle, data: dict):
    """
    Expected payload:
    {"cmd": "lock", "state": true, "success": true}

    Only writes to the DB when success=True — a failed command leaves the
    vehicle's state untouched, and the app is notified via WebSocket so it
    can clear its "pending" UI state and show an error.
    """
    cmd     = data.get("cmd")
    state   = bool(data.get("state", False))
    success = bool(data.get("success", False))

    attr = _ACK_CMD_TO_ATTR.get(cmd)
    if attr is None:
        logger.warning(f"Unknown ACK cmd '{cmd}' from vehicle {vehicle.id} — ignoring")
        return

    if success:
        setattr(vehicle, attr, state)
        logger.info(f"ACK applied — vehicle {vehicle.id} {attr}={state}")
    else:
        logger.warning(f"ACK reports failure — vehicle {vehicle.id} cmd={cmd} state={state}")

    _broadcast_threadsafe(_broadcast_ack(vehicle, cmd, state, success))


async def _broadcast_ack(vehicle, cmd: str, state: bool, success: bool):
    await ws_manager.broadcast(vehicle.id, {
        "type": "command_ack",
        "payload": {
            "cmd":     cmd,
            "state":   state,
            "success": success,
            # Echo current confirmed control states so the client can
            # reconcile in one shot instead of trusting only `state`.
            "is_armed":       vehicle.is_armed,
            "doors_locked":   vehicle.doors_locked,
            "mirror_fl":      vehicle.mirror_fl,
            "mirror_fr":      vehicle.mirror_fr,
            "mirror_rl":      vehicle.mirror_rl,
            "mirror_rr":      vehicle.mirror_rr,
            "engine_started": vehicle.engine_started,
            "ac_on":          vehicle.ac_on,
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