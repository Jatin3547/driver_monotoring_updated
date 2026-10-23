import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(String, ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(String, ForeignKey("vehicles.id"), nullable=True)
    trip_id: Mapped[str | None] = mapped_column(String, ForeignKey("trips.id"), nullable=True)
    safety_event_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("safety_events.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)  # low|medium|high
    status: Mapped[str] = mapped_column(String, default="open")  # open|reviewed|resolved
    location: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(String, default="")
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    driver: Mapped["Driver"] = relationship()
    vehicle: Mapped["Vehicle | None"] = relationship()
    trip: Mapped["Trip | None"] = relationship(back_populates="incidents")
    evidence: Mapped["Evidence | None"] = relationship(back_populates="incident", uselist=False)

