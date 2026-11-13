# app/models/gps_reading.py

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:  # imported only for type checkers; avoids a circular import
    from app.models.vehicle import Vehicle


class GPSReading(Base):
    __tablename__ = "gps_readings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,  # we always query by time range
    )

    vehicle: Mapped["Vehicle"] = relationship()

    def __repr__(self) -> str:
        return f"<GPSReading vehicle_id={self.vehicle_id} lat={self.latitude} lng={self.longitude}>"
