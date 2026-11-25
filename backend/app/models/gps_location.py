import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class GPSLocation(Base):
    """A timestamped simulated or authenticated browser GPS position."""

    __tablename__ = "gps_locations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0)
    heading: Mapped[float] = mapped_column(Float, default=0)
    acceleration_ms2: Mapped[float] = mapped_column(Float, default=0)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, default="simulation")  # simulation|live
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
