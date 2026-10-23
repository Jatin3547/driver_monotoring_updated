from datetime import datetime
from pydantic import BaseModel


class TripOut(BaseModel):
    id: str
    vehicleId: str
    driverId: str
    startTime: str
    endTime: str | None = None
    startLocation: str | None = None
    endLocation: str | None = None
    distanceKm: float = 0.0
    status: str
    driverName: str | None = None
    driverCode: str | None = None
    vehiclePlate: str | None = None
    vehicleCode: str | None = None
    incidentCount: int = 0


class TripCreate(BaseModel):
    driverCode: str
    vehicleCode: str
    startLocation: str = "Bengaluru Hub"
    endLocation: str | None = None


class TripUpdate(BaseModel):
    status: str | None = None  # in-progress | completed | cancelled
    endLocation: str | None = None
    distanceKm: float | None = None
