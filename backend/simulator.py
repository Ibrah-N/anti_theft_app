# simulator.py
# Run with: python3 simulator.py
# Simulates ESP32 publishing sensor, GPS, and status data to Mosquitto broker

import ssl
import json
import time
import random
import logging

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
MQTT_HOST     = os.getenv("MQTT_HOST")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# ── Device ID — must match vehicle.device_id in database ─────────────────────
DEVICE_ID = "esp-001"

# ── Topics ────────────────────────────────────────────────────────────────────
TOPIC_SENSORS = f"sg/{DEVICE_ID}/sensors"
TOPIC_GPS     = f"sg/{DEVICE_ID}/gps"
TOPIC_STATUS  = f"sg/{DEVICE_ID}/status"
TOPIC_ACK     = f"sg/{DEVICE_ID}/ack"

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
        logger.info(f"Subscribed to command topics for device {DEVICE_ID}")
    else:
        logger.error(f"❌ Connection failed: {reason_code}")


def on_message(client, userdata, message):
    topic   = message.topic
    payload = json.loads(message.payload.decode())
    logger.info(f"📥 Command received → {topic}: {payload}")

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


def publish_ack(cmd: str, state: bool, success: bool = True):
    """Confirm a command back to the backend — sg/{device_id}/ack."""
    ack_payload = {"cmd": cmd, "state": state, "success": success}
    client.publish(TOPIC_ACK, json.dumps(ack_payload), qos=1)
    logger.info(f"📡 ACK → {ack_payload}")


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