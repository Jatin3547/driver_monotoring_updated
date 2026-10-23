import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SafetyEvent(Base):
    """A single detection emitted by the AI monitoring pipeline (either the
    simulator or, when AI_MODE=live and the optional CV stack is installed,
    real inference). `source` always records which one produced it — the
    system never mislabels a simulated event as real."""

    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(String, ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)  # drowsiness|eye_closure|yawning|phone_use|distraction|no_presence
    severity: Mapped[str] = mapped_column(String)  # low|medium|high
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="simulation")  # simulation|live
    snapshot_url: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
