# simulator.py
# Run with: python3 simulator.py
# Simulates ESP32 publishing sensor, GPS, and status data to Mosquitto broker

import ssl
import json
import time
import random
import logging
import asyncio
import threading
import hmac
import hashlib
import base64
from datetime import datetime, timezone

import numpy as np
import cv2
from PIL import Image, ImageDraw
from av import VideoFrame
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    VideoStreamTrack,
)
from aiortc.sdp import candidate_from_sdp

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os


result = load_dotenv()
print("DEBUG load_dotenv():", result, "cwd:", os.getcwd(), "file:", __file__)

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

MQTT_HOST     = os.getenv("MQTT_HOST")
print("DEBUG MQTT_HOST:", repr(MQTT_HOST))

# ── Config ────────────────────────────────────────────────────────────────────
MQTT_HOST     = os.getenv("MQTT_HOST")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# ── TURN (coturn) — same shared secret as backend/app/core/config.py ─────────
# Used to mint our own short-lived TURN credentials, exactly like the app
# does via /vehicle/camera/ice-servers, so this simulator exercises the real
# relay path instead of assuming a direct connection is always possible.
TURN_SECRET = os.getenv("TURN_SECRET")
TURN_HOST   = os.getenv("TURN_HOST", "vigilx.duckdns.org")

# ── Video source ──────────────────────────────────────────────────────────────
# "webcam" = your real laptop camera (more realistic test — actual moving
# video, actual lighting/focus quirks a real ESP32-P4 feed would also have).
# "pattern" = the synthetic test-pattern track (no camera hardware needed,
# useful for headless/CI-style runs). Falls back to pattern automatically if
# the webcam can't be opened.
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "webcam")
CAMERA_INDEX  = int(os.getenv("CAMERA_INDEX", "0"))

# ── Device ID — must match vehicle.device_id in database ─────────────────────
DEVICE_ID = "esp-001"

# ── Command freshness ─────────────────────────────────────────────────────────
# Matches the app's own 10-second "pending" timeout. A command older than
# this was sent while the device was offline (or delayed some other way) —
# applying it now would be acting on a stale tap the user has already given
# up on. Refuse it instead: don't change state, don't send an ACK.
COMMAND_MAX_AGE_SECONDS = 10

def _is_command_expired(payload: dict) -> bool:
    ts_str = payload.get("ts")
    if not ts_str:
        return False  # no timestamp on the payload — nothing to judge, allow it
    try:
        sent_at = datetime.fromisoformat(ts_str)
    except ValueError:
        return False
    age = (datetime.now(timezone.utc) - sent_at).total_seconds()
    return age > COMMAND_MAX_AGE_SECONDS

# ── Topics ────────────────────────────────────────────────────────────────────
TOPIC_SENSORS = f"sg/{DEVICE_ID}/sensors"
TOPIC_GPS     = f"sg/{DEVICE_ID}/gps"
TOPIC_STATUS  = f"sg/{DEVICE_ID}/status"
TOPIC_ACK     = f"sg/{DEVICE_ID}/ack"
TOPIC_WEBRTC_OFFER = f"sg/{DEVICE_ID}/webrtc/offer"
TOPIC_WEBRTC_ICE   = f"sg/{DEVICE_ID}/webrtc/ice"

# ── GPS coordinates (Bara, KPK) ───────────────────────────────────────────────
BASE_LAT = 33.901206
BASE_LNG = 71.387076

# ── Device state — only changes when command received from backend ────────────
device_state = {
    "engine_on":      False,
    "fuel_flowing":   True,
    "is_armed":       True,
    "doors_locked":   True,
    "mirror_fl":      True,
    "mirror_fr":      True,
    "mirror_rl":      True,
    "mirror_rr":      True,
    "engine_started": False,
    "ac_on":          False,
}

# ── MQTT client setup ─────────────────────────────────────────────────────────
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smartguard_simulator",
)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT,
)


# ── Callbacks ─────────────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("✅ Simulator connected to broker")
        client.subscribe(f"sg/{DEVICE_ID}/cmd/engine",      qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/fuel",        qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/gps_request", qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/lock",        qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/mirror/+",    qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/start",       qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/ac",          qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/arm",         qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/camera/start", qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/camera/stop",  qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/webrtc/answer", qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/webrtc/ice",    qos=1)
        logger.info(f"Subscribed to command topics for device {DEVICE_ID}")
    else:
        logger.error(f"❌ Connection failed: {reason_code}")


def on_message(client, userdata, message):
    topic   = message.topic
    payload = json.loads(message.payload.decode())
    logger.info(f"📥 Command received → {topic}: {payload}")

    if _is_command_expired(payload):
        logger.warning(
            f"⏱️ Command on {topic} is stale (>{COMMAND_MAX_AGE_SECONDS}s old) "
            f"— dropping, no ACK sent"
        )
        return

    # ── Engine command ────────────────────────────────────────────────────────
    if topic.endswith("/cmd/engine"):
        device_state["engine_on"] = payload.get("state", False)
        state_str = "ON" if device_state["engine_on"] else "OFF"
        logger.info(f"🔑 Engine relay → {state_str}")
        # Confirm new state back to backend immediate   ly
        client.publish(TOPIC_STATUS, json.dumps(generate_status()), qos=1)
        logger.info(f"📡 Confirmed engine={state_str} to backend")

    # ── Fuel command ──────────────────────────────────────────────────────────
    elif topic.endswith("/cmd/fuel"):
        device_state["fuel_flowing"] = payload.get("state", True)
        state_str = "FLOWING" if device_state["fuel_flowing"] else "CUT"
        logger.info(f"⛽ Fuel relay → {state_str}")
        # Confirm new state back to backend immediately
        client.publish(TOPIC_STATUS, json.dumps(generate_status()), qos=1)
        logger.info(f"📡 Confirmed fuel={state_str} to backend")

    # ── GPS request ───────────────────────────────────────────────────────────
    elif topic.endswith("/cmd/gps_request"):
        gps_payload = generate_gps()
        client.publish(TOPIC_GPS, json.dumps(gps_payload), qos=1)
        logger.info(f"📡 GPS sent on request → {gps_payload}")

    # ── Door lock command ────────────────────────────────────────────────────
    elif topic.endswith("/cmd/lock"):
        state = payload.get("state", True)
        device_state["doors_locked"] = state
        logger.info(f"🔒 Doors → {'LOCKED' if state else 'UNLOCKED'}")
        publish_ack("lock", state)

    # ── Mirror command — sg/{id}/cmd/mirror/{position} ───────────────────────
    elif "/cmd/mirror/" in topic:
        position = topic.rsplit("/", 1)[-1]  # "fl" | "fr" | "rl" | "rr"
        state    = payload.get("state", True)
        key      = f"mirror_{position}"
        if key in device_state:
            device_state[key] = state
            logger.info(f"🪞 Mirror {position} → {'FOLDED' if state else 'UNFOLDED'}")
            publish_ack(key, state)
        else:
            logger.warning(f"Unknown mirror position: {position}")

    # ── Engine start (starter motor) command ─────────────────────────────────
    elif topic.endswith("/cmd/start"):
        state = payload.get("state", False)
        device_state["engine_started"] = state
        logger.info(f"⚡ Starter motor → {'ENGAGED' if state else 'DISENGAGED'}")
        publish_ack("start", state)

    # ── AC command ────────────────────────────────────────────────────────────
    elif topic.endswith("/cmd/ac"):
        state = payload.get("state", False)
        device_state["ac_on"] = state
        logger.info(f"❄️ AC → {'ON' if state else 'OFF'}")
        publish_ack("ac", state)

    # ── Arm / disarm command ──────────────────────────────────────────────────
    elif topic.endswith("/cmd/arm"):
        state = payload.get("state", True)
        device_state["is_armed"] = state
        logger.info(f"🛡️ Armed → {'ARMED' if state else 'DISARMED'}")
        publish_ack("arm", state)

    # ── Camera / WebRTC commands ─────────────────────────────────────────────
    # These hand off to the dedicated asyncio event loop (camera_loop, set up
    # below) since aiortc needs a real event loop to run — paho's on_message
    # callback itself is synchronous and can't await anything directly.
    elif topic.endswith("/cmd/camera/start"):
        call_id = payload.get("call_id")
        logger.info(f"📷 Camera start requested — call_id={call_id}")
        asyncio.run_coroutine_threadsafe(_camera_start(call_id), camera_loop)

    elif topic.endswith("/cmd/camera/stop"):
        logger.info("📷 Camera stop requested")
        asyncio.run_coroutine_threadsafe(_camera_stop(), camera_loop)

    elif topic.endswith("/cmd/webrtc/answer"):
        asyncio.run_coroutine_threadsafe(
            _camera_answer(payload.get("sdp"), payload.get("call_id")), camera_loop
        )

    elif topic.endswith("/cmd/webrtc/ice"):
        asyncio.run_coroutine_threadsafe(
            _camera_ice(payload, payload.get("call_id")), camera_loop
        )


def publish_ack(cmd: str, state: bool, success: bool = True):
    """Confirm a command back to the backend — sg/{device_id}/ack."""
    ack_payload = {"cmd": cmd, "state": state, "success": success}
    client.publish(TOPIC_ACK, json.dumps(ack_payload), qos=1)
    logger.info(f"📡 ACK → {ack_payload}")


# ── Camera / WebRTC subsystem ────────────────────────────────────────────────
# aiortc needs a real asyncio event loop, but the rest of this simulator is
# synchronous (paho's callback style). Rather than rewrite the whole file
# around asyncio, we run one dedicated event loop in its own background
# thread — exactly the same pattern the backend itself uses (main_event_loop
# + run_coroutine_threadsafe in mqtt_handlers.py) — and hand work to it from
# the synchronous MQTT callbacks above.
camera_loop = asyncio.new_event_loop()

def _start_camera_loop():
    asyncio.set_event_loop(camera_loop)
    camera_loop.run_forever()

threading.Thread(target=_start_camera_loop, daemon=True, name="camera-loop").start()

CAMERA_SESSION_MAX_SECONDS = 300  # 5 minutes — matches the app's own session cap

_pc: RTCPeerConnection | None = None
_current_call_id: str | None = None
_stop_handle = None  # camera_loop.call_later() handle, for the auto-timeout
_video_track = None  # explicit reference so we can release the webcam cleanly

class TestPatternTrack(VideoStreamTrack):
    """
    A synthetic video feed standing in for the real ESP32-P4 camera — a
    moving block plus a frame counter, so you can visually confirm in the
    app that frames are actually updating over time, not just that a
    connection was established. Swap this out for a real camera source once
    the hardware firmware exists; everything else in this file (signaling,
    TURN, session handling) stays the same.
    """
    kind = "video"

    def __init__(self):
        super().__init__()
        self._n = 0

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        img = Image.new("RGB", (320, 240), (20, 20, 30))
        draw = ImageDraw.Draw(img)
        x = int((self._n * 4) % 300)
        draw.rectangle([x, 100, x + 20, 140], fill=(0, 150, 255))
        draw.text((10, 10), f"VigilX simulator — frame {self._n}", fill=(255, 255, 255))
        draw.text((10, 220), DEVICE_ID, fill=(150, 150, 150))
        self._n += 1

        frame = VideoFrame.from_ndarray(np.array(img), format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

class WebcamTrack(VideoStreamTrack):
    """
    Your real laptop camera, captured via OpenCV — a much more realistic
    test than the synthetic pattern (actual motion, lighting, focus). Same
    interface as TestPatternTrack, so swapping between them is just a
    matter of which one gets passed to pc.addTrack().
    """
    kind = "video"

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        super().__init__()
        self._cap = cv2.VideoCapture(camera_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open webcam at index {camera_index}")
        logger.info(f"📷 Webcam opened — index={camera_index} {width}x{height}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        # cv2.VideoCapture.read() is blocking I/O — run it off the event
        # loop so it doesn't stall MQTT handling or anything else async.
        loop = asyncio.get_event_loop()
        ret, frame_bgr = await loop.run_in_executor(None, self._cap.read)
        if not ret:
            raise RuntimeError("Failed to read frame from webcam")

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self):
        super().stop()
        self._cap.release()
        logger.info("📷 Webcam released")


def _make_video_track():
    """Real webcam if requested and available, else the synthetic pattern —
    never crashes the whole camera session just because a webcam is busy or
    missing."""
    if CAMERA_SOURCE == "webcam":
        try:
            return WebcamTrack(camera_index=CAMERA_INDEX)
        except Exception as e:
            logger.warning(f"Could not open webcam ({e}) — falling back to test pattern")
    return TestPatternTrack()

    
def _turn_ice_config() -> RTCConfiguration:
    """Mint our own short-lived TURN credentials — same HMAC scheme as the
    backend's turn_credentials.py, so this simulator exercises the real
    relay path exactly like the app will."""
    if not TURN_SECRET:
        logger.warning("TURN_SECRET not set — falling back to STUN only")
        return RTCConfiguration(iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
        ])

    username = str(int(time.time()) + 3600)
    credential = base64.b64encode(
        hmac.new(TURN_SECRET.encode(), username.encode(), hashlib.sha1).digest()
    ).decode()

    return RTCConfiguration(iceServers=[
        RTCIceServer(urls="stun:stun.l.google.com:19302"),
        RTCIceServer(
            urls=[f"turn:{TURN_HOST}:3478", f"turn:{TURN_HOST}:3478?transport=tcp"],
            username=username,
            credential=credential,
        ),
    ])


async def _camera_start(call_id: str):
    global _pc, _current_call_id, _stop_handle, _video_track

    if _pc is not None:
        logger.info("Replacing existing camera session with new one")
        await _camera_stop()

    _current_call_id = call_id
    _pc = RTCPeerConnection(configuration=_turn_ice_config())
    _video_track = _make_video_track()
    _pc.addTrack(_video_track)

    @_pc.on("connectionstatechange")
    async def on_state_change():
        logger.info(f"📷 WebRTC connection state → {_pc.connectionState}")
        if _pc.connectionState in ("failed", "closed"):
            await _camera_stop()

    offer = await _pc.createOffer()
    await _pc.setLocalDescription(offer)

    # Non-trickle on our side: wait for ICE gathering to finish so the offer
    # already contains every candidate we know about in one shot. Simpler
    # and more reliable for a test simulator than implementing trickle ICE
    # both ways — the app may still trickle its own candidates for the
    # answer side, which _camera_ice() below handles either way.
    while _pc.iceGatheringState != "complete":
        await asyncio.sleep(0.1)

    client.publish(TOPIC_WEBRTC_OFFER, json.dumps({
        "sdp":     _pc.localDescription.sdp,
        "call_id": call_id,
    }), qos=1)
    logger.info(f"📷 WebRTC offer published — call_id={call_id}")

    _stop_handle = camera_loop.call_later(
        CAMERA_SESSION_MAX_SECONDS,
        lambda: asyncio.ensure_future(_camera_stop(), loop=camera_loop),
    )


async def _camera_answer(sdp: str, call_id: str):
    if _pc is None or call_id != _current_call_id:
        logger.warning(f"Ignoring WebRTC answer for unknown/stale call_id={call_id}")
        return
    await _pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="answer"))
    logger.info("📷 Remote description set — connecting...")


async def _camera_ice(data: dict, call_id: str):
    if _pc is None or call_id != _current_call_id:
        return
    candidate_str = data.get("candidate")
    if not candidate_str:
        return
    try:
        candidate = candidate_from_sdp(candidate_str.split(":", 1)[-1] if candidate_str.startswith("candidate:") else candidate_str)
        candidate.sdpMid        = data.get("sdpMid")
        candidate.sdpMLineIndex = data.get("sdpMLineIndex")
        await _pc.addIceCandidate(candidate)
    except Exception as e:
        logger.warning(f"Failed to add remote ICE candidate: {e}")


async def _camera_stop():
    global _pc, _current_call_id, _stop_handle, _video_track
    if _stop_handle:
        _stop_handle.cancel()
        _stop_handle = None
    if _video_track:
        _video_track.stop()
        _video_track = None
    if _pc:
        await _pc.close()
        _pc = None
    logger.info(f"📷 WebRTC session ended — call_id={_current_call_id}")
    _current_call_id = None


# ── Wire callbacks ────────────────────────────────────────────────────────────
client.on_connect = on_connect
client.on_message = on_message


# ── Data generators ───────────────────────────────────────────────────────────
def generate_sensors(open_zone: str = None) -> dict:
    data = {
        "zone_fl":     True,
        "zone_fr":     True,
        "zone_rl":     True,
        "zone_rr":     True,
        "zone_bonnet": True,
        "zone_trunk":  True,
    }
    if open_zone and open_zone in data:
        data[open_zone] = False
    return data


def generate_gps() -> dict:
    return {
        "latitude":  BASE_LAT + random.uniform(-0.001, 0.001),
        "longitude": BASE_LNG + random.uniform(-0.001, 0.001),
        "speed_kmh": round(random.uniform(0, 60), 1),
        "city":      "Bara",
        "address":   "Khyber Agency, KPK",
    }


def generate_status() -> dict:
    """Always reflects real device_state for engine, fuel, and arm state."""
    return {
        "battery_level": round(random.uniform(11.8, 12.8), 1),
        "signal_bars":   random.randint(2, 4),
        "engine_on":     device_state["engine_on"],
        "fuel_flowing":  device_state["fuel_flowing"],
        "is_armed":      device_state["is_armed"],
    }


# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    logger.info(f"Starting simulator for device: {DEVICE_ID}")
    logger.info(f"Connecting to {MQTT_HOST}:{MQTT_PORT}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    time.sleep(2)  # wait for connection

    step = 0
    logger.info("Publishing data every 5 seconds — press Ctrl+C to stop")
    logger.info("=" * 60)

    while True:
        try:
            if not device_state["is_armed"]:
                # ── Sleep mode ────────────────────────────────────────────────
                # Disarmed = no periodic telemetry, matching real firmware
                # behavior (saves power/heat instead of running 24/7). The
                # device still listens for commands (arm, lock, etc.) via the
                # MQTT loop running in its own thread — only this publish loop
                # goes quiet.
                if step % 6 == 0:
                    logger.info("😴 Disarmed — sleeping (no telemetry published)")
                step += 1
                time.sleep(5)
                continue

            # ── Status every 5 seconds ────────────────────────────────────────
            status_payload = generate_status()

            client.publish(TOPIC_STATUS, json.dumps(status_payload), qos=1)
            logger.info(
                f"📡 STATUS → battery={status_payload['battery_level']}V "
                f"engine={'ON' if status_payload['engine_on'] else 'OFF'} "
                f"fuel={'FLOW' if status_payload['fuel_flowing'] else 'CUT'}"
            )

            # ── Sensors every 3rd cycle ───────────────────────────────────────
            if step % 3 == 0:
                # Randomly open a zone every 9th cycle to test alerts
                if step % 3 == 0 and step > 0:
                    open_zone = random.choice([
                        "zone_fl", "zone_fr", "zone_trunk", "zone_bonnet"
                    ])
                    logger.warning(f"🚨 Simulating zone open: {open_zone}")
                else:
                    open_zone = None

                sensor_payload = generate_sensors(open_zone)
                client.publish(TOPIC_SENSORS, json.dumps(sensor_payload), qos=1)
                logger.info(f"📡 SENSORS → {sensor_payload}")

            step += 1
            time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Simulator stopped by user")
            break

    client.loop_stop()
    client.disconnect()
    logger.info("Simulator disconnected")


if __name__ == "__main__":
    run()