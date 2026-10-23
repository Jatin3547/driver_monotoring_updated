from pydantic import BaseModel


class VehicleLocationOut(BaseModel):
    vehicleId: str
    lat: float
    lng: float
    speedKmh: float
    heading: float
    accelerationMs2: float
    source: str
    timestamp: str
