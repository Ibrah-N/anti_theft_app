# Okay let's take a back step and then re-continue with a smaller resolution then the one we currently dealing with.

import asyncio
import logging
import threading

import firebase_admin
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials

import app.models  # noqa: F401  (registers every model with SQLAlchemy before first use)
from app.core.config import settings

# Import routers
from app.routes import alerts, auth, device, gps, vehicle, ws
from app.services.media_cleanup import start_cleanup_thread
from app.services.mqtt_handlers import handle_mqtt_message
from app.services.mqtt_service import mqtt_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Anti-theft vehicle security system API",
    version="1.0.0",
    debug=settings.DEBUG,
)

# ── CORS — allows Flutter app to talk to this API ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(vehicle.router, prefix="/api/vehicle", tags=["Vehicle"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(gps.router, prefix="/api/gps", tags=["GPS"])
app.include_router(device.router, prefix="/api/device", tags=["Device"])
app.include_router(ws.router, tags=["WebSocket"])


# ── Event Handler ──────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin initialized")

    from app.services import mqtt_handlers

    mqtt_handlers.main_event_loop = asyncio.get_event_loop()

    thread = threading.Thread(target=mqtt_service.connect, daemon=True)
    thread.start()
    mqtt_service.set_db_callback(handle_mqtt_message)
    logger.info("MQTT service starting in background thread")

    start_cleanup_thread()


@app.on_event("shutdown")
def shutdown():
    mqtt_service.disconnect()
    logger.info("MQTT service stopped")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "app": settings.APP_NAME}


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "mqtt_connected": mqtt_service.is_connected,
    }


#    sudo apt install -y ffmpeg
#    client_max_body_size 32m;
