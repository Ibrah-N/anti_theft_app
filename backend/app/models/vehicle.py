from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id:           Mapped[int]   = mapped_column(primary_key=True, index=True)
    owner_id:     Mapped[int]   = mapped_column(ForeignKey("users.id"), nullable=False)
    name:         Mapped[str]   = mapped_column(String(100), nullable=False)
    reg_number:   Mapped[str]   = mapped_column(String(50), unique=True, nullable=False)
    device_id:    Mapped[str]   = mapped_column(String(100), unique=True, nullable=False)

    # Live state — updated by MQTT in Step 3
    engine_on:    Mapped[bool]  = mapped_column(Boolean, default=False)
    fuel_flowing: Mapped[bool]  = mapped_column(Boolean, default=True)
    speed_kmh:    Mapped[float] = mapped_column(Float, default=0.0)
    battery_level:Mapped[float] = mapped_column(Float, default=12.6)
    signal_bars:  Mapped[int]   = mapped_column(Integer, default=3)

    # Zone states — True = closed/secure, False = open/alert
    zone_fl:      Mapped[bool]  = mapped_column(Boolean, default=True)  # front left
    zone_fr:      Mapped[bool]  = mapped_column(Boolean, default=True)  # front right
    zone_rl:      Mapped[bool]  = mapped_column(Boolean, default=True)  # rear left
    zone_rr:      Mapped[bool]  = mapped_column(Boolean, default=True)  # rear right
    zone_bonnet:  Mapped[bool]  = mapped_column(Boolean, default=True)
    zone_trunk:   Mapped[bool]  = mapped_column(Boolean, default=True)

    created_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    owner:  Mapped["User"]        = relationship(back_populates="vehicles")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="vehicle")

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} reg={self.reg_number}>"