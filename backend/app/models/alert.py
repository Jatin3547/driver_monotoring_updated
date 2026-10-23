import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Alert(Base):
    """A dashboard-facing notification. Delivery is local/in-app only —
    designed so an email/SMS/push channel can be added later by having a
    notifier subscribe to the same creation event (see app/services/alert_service.py)."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)  # low|medium|high
    driver_id: Mapped[str | None] = mapped_column(String, ForeignKey("drivers.id"), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String, ForeignKey("vehicles.id"), nullable=True)
    message: Mapped[str] = mapped_column(String)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
