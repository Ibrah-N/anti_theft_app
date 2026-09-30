# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "SmartGuard"
    DEBUG: bool = True

    # MQTT
    MQTT_HOST:      str
    MQTT_PORT:      int = 8883
    MQTT_USERNAME:  str
    MQTT_PASSWORD:  str
    MQTT_CLIENT_ID: str = "smartguard_backend"

        # TURN (coturn) — must match static-auth-secret in /etc/turnserver.conf
    # No default here on purpose — this must come from .env only. (A real
    # secret was previously hardcoded here as a default and got committed to
    # git; treat that value as burned and rotate it again in
    # /etc/turnserver.conf + every .env that references it.)
    TURN_SECRET: str
    TURN_HOST:   str = "vigilx.duckdns.org"

    # Camera media (snapshots / recordings) — uploaded by whichever side
    # currently holds the WebRTC video (the app today, the camera firmware
    # later), since video no longer passes through this backend at all.
    MEDIA_ROOT:                str = "/var/vigilx-media"
    MEDIA_MIN_FREE_BYTES:      int = 500 * 1024 * 1024   # refuse uploads below 500 MB free
    MEDIA_MAX_SNAPSHOT_BYTES:  int = 5 * 1024 * 1024     # 5 MB
    MEDIA_MAX_RECORDING_BYTES: int = 200 * 1024 * 1024   # matches the 5-min session cap

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )



# Single instance imported everywhere
settings = Settings()