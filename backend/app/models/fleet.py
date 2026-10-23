import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Fleet(Base):
    """A named group of vehicles. Minimal on purpose — a fleet-management
    org may only ever have one fleet, but the model exists so multi-fleet
    setups are possible without a schema change."""

    __tablename__ = "fleets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="fleet")
