from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id:         Mapped[int]  = mapped_column(primary_key=True, index=True)
    user_id:    Mapped[int]  = mapped_column(ForeignKey("users.id"), nullable=False)
    fcm_token:  Mapped[str]  = mapped_column(String(255), unique=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<DeviceToken id={self.id} user_id={self.user_id}>"