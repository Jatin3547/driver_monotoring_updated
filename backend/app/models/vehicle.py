import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)  # e.g. VEH-001
    plate_number: Mapped[str] = mapped_column(String, nullable=False)
    make: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String, default="car")  # truck|van|car|bus
    status: Mapped[str] = mapped_column(String, default="active")  # active|idle|maintenance|offline
    odometer_km: Mapped[float] = mapped_column(Float, default=0)
    fuel_level: Mapped[int] = mapped_column(Integer, default=100)
    last_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_service_due_km: Mapped[float] = mapped_column(Float, default=0)

    fleet_id: Mapped[str | None] = mapped_column(String, ForeignKey("fleets.id"), nullable=True)
    fleet: Mapped["Fleet | None"] = relationship(back_populates="vehicles")

    assigned_driver: Mapped["Driver | None"] = relationship(
        back_populates="assigned_vehicle",
        foreign_keys="Driver.assigned_vehicle_id",
        uselist=False,
    )
