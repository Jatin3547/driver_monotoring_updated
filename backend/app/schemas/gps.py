from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleLocationOut(BaseModel):
    vehicleId: str
    lat: float
    lng: float
    speedKmh: float
    heading: float
    accelerationMs2: float
    accuracyM: float | None = None
    source: str
    gpsStatus: str
    staleAfterSeconds: int
    timestamp: str


class DriverGPSUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(gt=0, le=10000)
    speed: float | None = Field(default=None, ge=0, le=100)  # browser reports m/s
    heading: float | None = Field(default=None, ge=0, le=360)
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value
