from pydantic import BaseModel


class AlertOut(BaseModel):
    id: str
    type: str
    severity: str
    driverId: str | None = None
    vehicleId: str | None = None
    message: str
    timestamp: str
    read: bool
