from datetime import datetime, timezone
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base

class AlertCategory(str, enum.Enum):
    engine = "engine"
    gps    = "gps"
    door   = "door"
    system = "system"

class AlertSeverity(str, enum.Enum):
    critical = "critical"
    warning  = "warning"
    info     = "info"

class Alert(Base):
    __tablename__ = "alerts"

    id:          Mapped[int]  = mapped_column(primary_key=True, index=True)
    vehicle_id:  Mapped[int]  = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    title:       Mapped[str]  = mapped_column(String(200), nullable=False)
    description: Mapped[str]  = mapped_column(String(500), nullable=False)
    category:    Mapped[AlertCategory]  = mapped_column(
        Enum(AlertCategory), nullable=False
    )
    severity:    Mapped[AlertSeverity]  = mapped_column(
        Enum(AlertSeverity), nullable=False
    )
    is_read:     Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True   # we query alerts by time frequently
    )

    # Relationship
    vehicle: Mapped["Vehicle"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id} title={self.title}>"