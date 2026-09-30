# app/models/camera_media.py

from datetime import datetime, timezone
import enum

from sqlalchemy import String, BigInteger, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CameraMediaType(str, enum.Enum):
    snapshot  = "snapshot"
    recording = "recording"


class CameraMedia(Base):
    __tablename__ = "camera_media"

    id:               Mapped[int]  = mapped_column(primary_key=True, index=True)
    vehicle_id:       Mapped[int]  = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    media_type:       Mapped[CameraMediaType] = mapped_column(Enum(CameraMediaType), nullable=False)

    # Absolute path on the server's disk (see settings.MEDIA_ROOT) — not
    # exposed directly to clients; downloads always go through the
    # /camera/media/{id}/file route so ownership is checked every time.
    file_path:        Mapped[str]  = mapped_column(String(500), nullable=False)
    file_size_bytes:  Mapped[int]  = mapped_column(BigInteger, nullable=False)

    # Only set for recordings — null for snapshots.
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at:       Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,  # listed newest-first constantly
    )

    vehicle: Mapped["Vehicle"] = relationship()

    def __repr__(self) -> str:
        return f"<CameraMedia id={self.id} type={self.media_type} vehicle={self.vehicle_id}>"