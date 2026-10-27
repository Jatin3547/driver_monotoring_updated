import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)  # e.g. DRV-001
    name: Mapped[str] = mapped_column(String, nullable=False)
    license_number: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")  # active|on-trip|off-duty|suspended
    safety_score: Mapped[int] = mapped_column(Integer, default=100)
    joined_date: Mapped[date] = mapped_column(Date)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0)
    incident_count: Mapped[int] = mapped_column(Integer, default=0)

    # Optional link to a User account (populated for driver-role users)
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )

    assigned_vehicle_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("vehicles.id"), nullable=True
    )
    assigned_vehicle: Mapped["Vehicle | None"] = relationship(
        back_populates="assigned_driver", foreign_keys=[assigned_vehicle_id]
    )
