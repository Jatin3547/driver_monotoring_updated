from pydantic import BaseModel


class IncidentOut(BaseModel):
    id: str
    driverId: str
    vehicleId: str | None = None
    tripId: str | None = None
    evidenceId: str | None = None
    snapshotUrl: str | None = None
    type: str
    severity: str
    status: str
    timestamp: str
    location: str
    description: str
    acknowledgedBy: str | None = None


class IncidentCreate(BaseModel):
    driverId: str
    vehicleId: str | None = None
    tripId: str | None = None
    type: str
    severity: str
    location: str = ""
    description: str = ""
    snapshotUrl: str | None = None


class IncidentUpdate(BaseModel):
    status: str | None = None
    acknowledgedBy: str | None = None

