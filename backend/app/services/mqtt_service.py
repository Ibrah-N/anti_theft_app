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

def topic_cmd_lock(device_id: str) -> str:
    return f"sg/{device_id}/cmd/lock"

def topic_cmd_mirror(device_id: str, position: str) -> str:
    # position: "fl" | "fr" | "rl" | "rr"
    return f"sg/{device_id}/cmd/mirror/{position}"

def topic_cmd_start(device_id: str) -> str:
    return f"sg/{device_id}/cmd/start"

def topic_cmd_ac(device_id: str) -> str:
    return f"sg/{device_id}/cmd/ac"

def topic_cmd_arm(device_id: str) -> str:
    return f"sg/{device_id}/cmd/arm"

def topic_ack(device_id: str) -> str:
    return f"sg/{device_id}/ack"

def topic_cmd_camera_start(device_id: str) -> str:
    return f"sg/{device_id}/cmd/camera/start"

def topic_cmd_camera_stop(device_id: str) -> str:
    return f"sg/{device_id}/cmd/camera/stop"

def topic_cmd_webrtc_answer(device_id: str) -> str:
    return f"sg/{device_id}/cmd/webrtc/answer"

def topic_cmd_webrtc_ice(device_id: str) -> str:
    return f"sg/{device_id}/cmd/webrtc/ice"

def topic_webrtc_offer(device_id: str) -> str:
    return f"sg/{device_id}/webrtc/offer"

def topic_webrtc_ice(device_id: str) -> str:
    return f"sg/{device_id}/webrtc/ice"

def topic_camera_state(device_id: str) -> str:
    return f"sg/{device_id}/camera/state"


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
            client.subscribe("sg/+/ack",     qos=1)
            client.subscribe("sg/+/webrtc/offer", qos=1)
            client.subscribe("sg/+/webrtc/ice",   qos=1)
            client.subscribe("sg/+/camera/state", qos=1)
            logger.info(
                "Subscribed to sg/+/sensors, sg/+/gps, sg/+/status, sg/+/ack, "
                "sg/+/webrtc/offer, sg/+/webrtc/ice, sg/+/camera/state"
            )
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
        elif topic.endswith("/ack"):
            self._handle_ack(device_id, data)
        elif topic.endswith("/webrtc/offer"):
            self._handle_webrtc_offer(device_id, data)
        elif topic.endswith("/webrtc/ice"):
            self._handle_webrtc_ice(device_id, data)
        elif topic.endswith("/camera/state"):
            self._handle_camera_state(device_id, data)

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

    def _handle_ack(self, device_id: str, data: dict):
        """Device confirms a command was applied — {"cmd", "state", "success"}."""
        if self._db_callback:
            self._db_callback("ack", device_id, data)

    def _handle_webrtc_offer(self, device_id: str, data: dict):
        """Device's SDP offer, starting a WebRTC handshake — {"sdp", "call_id"}."""
        if self._db_callback:
            self._db_callback("webrtc_offer", device_id, data)

    def _handle_webrtc_ice(self, device_id: str, data: dict):
        """Device's ICE candidate — {"candidate", "sdpMid", "sdpMLineIndex", "call_id"}."""
        if self._db_callback:
            self._db_callback("webrtc_ice", device_id, data)

    def _handle_camera_state(self, device_id: str, data: dict):
        """
        Camera reports what it is doing —
        {"state": "idle|recording|uploading|streaming", "clip_id", "reason",
         "elapsed_s", "segments_uploaded", "segments_total"}.
        """
        if self._db_callback:
            self._db_callback("camera_state", device_id, data)


    # ── Publish commands ───────────────────────────────────────────────────────
    def publish_engine_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_engine(device_id),
            payload,
            qos=1,          # QoS 1 = at least once delivery
            retain=False,    # one-shot command — never replay a stale tap
        )
        logger.info(f"Published engine command → {device_id}: {state}")

    def publish_fuel_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_fuel(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published fuel command → {device_id}: {state}")

    def publish_lock_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_lock(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published lock command → {device_id}: {state}")

    def publish_mirror_command(self, device_id: str, position: str, state: bool):
        # position: "fl" | "fr" | "rl" | "rr" — state True = fold
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_mirror(device_id, position),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published mirror_{position} command → {device_id}: {state}")

        def publish_camera_start_command(self, device_id: str, call_id: str,
                                     finalize_recording: bool = True):
        # finalize_recording=True tells the camera: if you are recording an
        # event clip right now, close that file safely, start the live stream
        # FIRST, and upload the finished clip afterwards (stream-first).
        # Older firmware simply ignores the extra field.
        payload = json.dumps({
            "call_id": call_id,
            "finalize_recording": finalize_recording,
            "ts": self._ts(),
        })
        self.client.publish(
            topic_cmd_start(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published start command → {device_id}: {state}")

    def publish_ac_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_ac(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published AC command → {device_id}: {state}")

    def publish_arm_command(self, device_id: str, state: bool):
        payload = json.dumps({"state": state, "ts": self._ts()})
        self.client.publish(
            topic_cmd_arm(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published arm command → {device_id}: {state}")

    def publish_camera_start_command(self, device_id: str, call_id: str):
        payload = json.dumps({"call_id": call_id, "ts": self._ts()})
        self.client.publish(
            topic_cmd_camera_start(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published camera start command → {device_id} call_id={call_id}")

    def publish_camera_stop_command(self, device_id: str, call_id: str):
        payload = json.dumps({"call_id": call_id, "ts": self._ts()})
        self.client.publish(
            topic_cmd_camera_stop(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published camera stop command → {device_id} call_id={call_id}")

    def publish_webrtc_answer(self, device_id: str, sdp: str, call_id: str):
        payload = json.dumps({"sdp": sdp, "call_id": call_id, "ts": self._ts()})
        self.client.publish(
            topic_cmd_webrtc_answer(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published WebRTC answer → {device_id} call_id={call_id}")

    def publish_webrtc_ice(self, device_id: str, candidate: dict, call_id: str):
        payload = json.dumps({**candidate, "call_id": call_id, "ts": self._ts()})
        self.client.publish(
            topic_cmd_webrtc_ice(device_id),
            payload,
            qos=1,
            retain=False,
        )
        logger.info(f"Published WebRTC ICE candidate → {device_id} call_id={call_id}")

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