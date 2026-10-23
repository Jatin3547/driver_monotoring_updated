import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Evidence(Base):
    """Metadata record for event-triggered video or image evidence.
    
    Actual video clips and images are stored as files on disk (e.g. in
    data/evidence/), NEVER as binary blobs in ordinary database rows.
    This model records protected metadata, duration, retention status,
    and foreign-key links to the associated incident, driver, vehicle, and trip.
    """

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String, ForeignKey("incidents.id"), unique=True, index=True
    )
    safety_event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("safety_events.id"), nullable=True
    )
    driver_id: Mapped[str] = mapped_column(String, ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), index=True)
    trip_id: Mapped[str | None] = mapped_column(String, ForeignKey("trips.id"), nullable=True)

    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, default="video/mp4")  # video/mp4 | image/jpeg
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, default=8.0)
    pre_event_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    post_event_seconds: Mapped[float] = mapped_column(Float, default=3.0)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    incident: Mapped["Incident"] = relationship(back_populates="evidence")
    driver: Mapped["Driver"] = relationship()
    vehicle: Mapped["Vehicle"] = relationship()
    trip: Mapped["Trip | None"] = relationship()
