from pydantic import BaseModel


class VehicleOut(BaseModel):
    id: str
    plateNumber: str
    model: str
    make: str
    year: int
    type: str
    status: str
    assignedDriverId: str | None = None
    odometerKm: float
    fuelLevel: int
    lastServiceDate: str
    nextServiceDueKm: float
