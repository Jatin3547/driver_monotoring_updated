from datetime import date

from pydantic import BaseModel


class DriverOut(BaseModel):
    id: str
    name: str
    licenseNumber: str
    phone: str
    email: str
    status: str
    safetyScore: int
    assignedVehicleId: str | None = None
    joinedDate: date
    totalTrips: int
    totalDistanceKm: float
    incidentCount: int

    class Config:
        from_attributes = True
