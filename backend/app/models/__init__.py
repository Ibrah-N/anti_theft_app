# app/models/__init__.py

from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.alert import Alert
from app.models.gps_reading import GPSReading

__all__ = ["User", "Vehicle", "Alert", "GPSReading"]