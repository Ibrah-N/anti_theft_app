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
    TURN_SECRET: str = "c50f6f08b4228ef7a8f4474d855c1b292586eedbd4cfa25b8818471f72cf5ae3"
    TURN_HOST:   str = "vigilx.duckdns.org"


    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )



# Single instance imported everywhere
settings = Settings()