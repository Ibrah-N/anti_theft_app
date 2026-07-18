# app/services/mqtt_service.py

import ssl
import json
import logging
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Topic constants ────────────────────────────────────────────────────────────
def topic_sensors(device_id: str) -> str:
    return f"sg/{device_id}/sensors"

def topic_gps(device_id: str) -> str:
    return f"sg/{device_id}/gps"

def topic_status(device_id: str) -> str:
    return f"sg/{device_id}/status"

def topic_cmd_engine(device_id: str) -> str:
    return f"sg/{device_id}/cmd/engine"

def topic_cmd_fuel(device_id: str) -> str:
    return f"sg/{device_id}/cmd/fuel"


# ── MQTT Service ───────────────────────────────────────────────────────────────
class MQTTService:
    def __init__(self):
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.MQTT_CLIENT_ID,
        )
        self.client.username_pw_set(
            settings.MQTT_USERNAME,
            settings.MQTT_PASSWORD,
        )
#        self.client.tls_set(
#            cert_reqs=ssl.CERT_REQUIRED,
#            tls_version=ssl.PROTOCOL_TLS_CLIENT,
#        )
        self._connected   = False
        self._db_callback = None   # injected after startup to avoid circular imports

        # Wire callbacks
        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message    = self._on_message

    # ── Connection ─────────────────────────────────────────────────────────────
    def connect(self):
        self.client.connect(
            settings.MQTT_HOST,
            settings.MQTT_PORT,
            keepalive=60,
        )
        # loop_start() runs the network loop in a background thread
        self.client.loop_start()
        logger.info(f"MQTT connecting to {settings.MQTT_HOST}:{settings.MQTT_PORT}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT disconnected")

    def set_db_callback(self, callback):
        """Inject the DB handler after app startup to avoid circular imports."""
        self._db_callback = callback

    # ── Callbacks ──────────────────────────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            logger.info("✅ MQTT connected to broker")
            # Subscribe to all device topics using wildcard
            client.subscribe("sg/+/sensors", qos=1)
            client.subscribe("sg/+/gps",     qos=1)
            client.subscribe("sg/+/status",  qos=1)
            logger.info("Subscribed to sg/+/sensors, sg/+/gps, sg/+/status")
        else:
            logger.error(f"❌ MQTT connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        logger.warning(f"MQTT disconnected — reason: {reason_code}")

    def _on_message(self, client, userdata, message):
        topic   = message.topic
        payload = message.payload.decode("utf-8")
        logger.info(f"MQTT message received → topic: {topic}")

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON on topic {topic}: {payload}")
            return

        # Extract device_id from topic — sg/{device_id}/sensors
        parts     = topic.split("/")
        device_id = parts[1] if len(parts) >= 2 else None

        if not device_id:
            logger.error(f"Could not extract device_id from topic: {topic}")
            return

        # Route to correct handler
        if topic.endswith("/sensors"):
            self._handle_sensors(device_id, data)
        elif topic.endswith("/gps"):
            self._handle_gps(device_id, data)
        elif topic.endswith("/status"):
            self._handle_status(device_id, data)

    # ── Message handlers ───────────────────────────────────────────────────────
    def _handle_sensors(self, device_id: str, data: dict):
        """Update zone states + trigger alerts for open zones."""
        if self._db_callback:
            self._db_callback("sensors", device_id, data)

    def _handle_gps(self, device_id: str, data: dict):
        """Insert new GPS reading + update vehicle speed."""
        if self._db_callback:
            self._db_callback("gps", device_id, data)

    def _handle_status(self, device_id: str, data: dict):
        """Update battery, signal bars, connectivity."""
        if self._db_callback:
            self._db_callback("status", device_id, data)

    # ── Publish commands ───────────────────────────────────────────────────────
    def publish_engine_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_engine(device_id),
            payload,
            qos=1,          # QoS 1 = at least once delivery
            retain=True,    # device gets command even if briefly offline
        )
        logger.info(f"Published engine command → {device_id}: {state}")

    def publish_fuel_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_fuel(device_id),
            payload,
            qos=1,
            retain=True,
        )
        logger.info(f"Published fuel command → {device_id}: {state}")

    def publish_gps_request(self, device_id: str):
        if not self._connected:
            logger.error("Cannot publish GPS request — MQTT not connected")
            return

        payload = json.dumps({"cmd": "gps_request", "ts": self._ts()})
        result  = self.client.publish(
            f"sg/{device_id}/cmd/gps_request",
            payload,
            qos=1,
        )
        logger.info(
            f"Published GPS request → {device_id} "
            f"(rc={result.rc} mid={result.mid})"
        )

    @staticmethod
    def _ts() -> str:
        return datetime.now(timezone.utc).isoformat()

    @property
    def is_connected(self) -> bool:
        return self._connected
    

# ── Singleton — imported everywhere ───────────────────────────────────────────
mqtt_service = MQTTService()
