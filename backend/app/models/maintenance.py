import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String)
    cost: Mapped[float] = mapped_column(Float, default=0)
    odometer_km_at_service: Mapped[float] = mapped_column(Float, default=0)
    next_due_km: Mapped[float] = mapped_column(Float, default=0)
