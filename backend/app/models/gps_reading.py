# app/models/gps_reading.py

from datetime import datetime, timezone
from sqlalchemy import Float, ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class GPSReading(Base):
    __tablename__ = "gps_readings"

    id:         Mapped[int]   = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int]   = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)

    latitude:   Mapped[float] = mapped_column(Float, nullable=False)
    longitude:  Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh:  Mapped[float] = mapped_column(Float, default=0.0)
    city:       Mapped[str]   = mapped_column(String(100), nullable=True)
    address:    Mapped[str]   = mapped_column(String(255), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True   # we always query by time range
    )

    vehicle: Mapped["Vehicle"] = relationship()

    def __repr__(self) -> str:
        return f"<GPSReading vehicle_id={self.vehicle_id} lat={self.latitude} lng={self.longitude}>"