from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base

# Import models so Base knows about them before create_all
from app.models import User, Vehicle, Alert

# Import routers
from app.routes import auth, vehicle, alerts, gps

# ── Create tables if they don't exist ────────────────────────────────────────
# Base.metadata.create_all(bind=engine)

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
app.include_router(auth.router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(vehicle.router, prefix="/api/vehicle", tags=["Vehicle"])
app.include_router(alerts.router,  prefix="/api/alerts",  tags=["Alerts"])
app.include_router(gps.router,    prefix="/api/gps",     tags=["GPS"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "app": settings.APP_NAME}