import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), index=True)
    driver_id: Mapped[str] = mapped_column(String, ForeignKey("drivers.id"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_location: Mapped[str] = mapped_column(String, nullable=True)
    end_location: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="completed")  # in-progress|completed|cancelled

    # Relationships
    driver: Mapped["Driver"] = relationship()
    vehicle: Mapped["Vehicle"] = relationship()
    incidents: Mapped[list["Incident"]] = relationship(back_populates="trip")

