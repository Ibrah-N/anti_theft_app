from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]  = mapped_column(primary_key=True, index=True)
    email:      Mapped[str]  = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone:      Mapped[str]  = mapped_column(String(20),  unique=True, index=True, nullable=True)
    full_name:  Mapped[str]  = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active:  Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified:Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationship — one user can have one vehicle (expandable later)
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="owner")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"