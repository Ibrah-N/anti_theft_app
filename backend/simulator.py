# simulator.py
# Run with: python3 simulator.py
# Simulates ESP32 publishing sensor, GPS, and status data to EMQX

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

# ── Change this to match your registered vehicle's device_id ─────────────────
DEVICE_ID = "ESP_012"

# ── Topics ────────────────────────────────────────────────────────────────────
TOPIC_SENSORS = f"sg/{DEVICE_ID}/sensors"
TOPIC_GPS     = f"sg/{DEVICE_ID}/gps"
TOPIC_STATUS  = f"sg/{DEVICE_ID}/status"

# ── Islamabad GPS coordinates (simulate movement around F-8) ─────────────────
BASE_LAT = 33.6844
BASE_LNG = 73.0479


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


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("✅ Simulator connected to EMQX broker")
        # Subscribe to command topics so we can see commands coming back
        client.subscribe(f"sg/{DEVICE_ID}/cmd/engine", qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/fuel",   qos=1)
        client.subscribe(f"sg/{DEVICE_ID}/cmd/gps_request", qos=1)
        logger.info(f"Subscribed to command topics for device {DEVICE_ID}")
    else:
        logger.error(f"❌ Connection failed: {reason_code}")


# ── Data generators ───────────────────────────────────────────────────────────
def generate_sensors(open_zone: str = None) -> dict:
    """
    All zones closed by default.
    Pass open_zone='zone_trunk' to simulate trunk opening etc.
    """
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


def generate_gps(step: int) -> dict:
    """Simulate slow movement around base coordinates."""
    return {
        "latitude":  round(BASE_LAT + step * 0.0001, 6),
        "longitude": round(BASE_LNG + step * 0.0001, 6),
        "speed_kmh": round(random.uniform(0, 60), 1),
        "city":      "Islamabad",
        "address":   "F-8 Markaz, Islamabad",
    }


def generate_status() -> dict:
    return {
        "battery_level": round(random.uniform(11.8, 12.8), 1),
        "signal_bars":   random.randint(2, 4),
        "engine_on":     False,
        "fuel_flowing":  True,
    }



def on_message(client, userdata, message):
    topic   = message.topic
    payload = json.loads(message.payload.decode())
    logger.info(f"📥 Command received → {topic}: {payload}")

    # Respond to GPS request with one reading
    if topic.endswith("/cmd/gps_request"):
        gps_payload = generate_gps(random.randint(0, 100))
        client.publish(TOPIC_GPS, json.dumps(gps_payload), qos=1)
        logger.info(f"📡 GPS sent on request → {gps_payload}")


# ── Wire callbacks AFTER functions are defined ────────────────────────────────
client.on_connect = on_connect
client.on_message = on_message


# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    logger.info(f"Starting simulator for device: {DEVICE_ID}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    # Wait for connection
    time.sleep(2)

    step = 0

    logger.info("Publishing data every 5 seconds — press Ctrl+C to stop")
    logger.info("=" * 60)

    while True:
        try:
            # ── Status every 5 seconds ────────────────────────────────
            status_payload = generate_status()
            client.publish(TOPIC_STATUS, json.dumps(status_payload), qos=1)
            logger.info(f"📡 STATUS → battery={status_payload['battery_level']}V")

            # ── Sensors every 3rd cycle ───────────────────────────────
            if step % 3 == 0:
                if step % 9 == 0 and step > 0:
                    open_zone = random.choice([
                        "zone_fl", "zone_fr", "zone_trunk", "zone_bonnet"
                    ])
                    logger.warning(f"🚨 Zone open: {open_zone}")
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