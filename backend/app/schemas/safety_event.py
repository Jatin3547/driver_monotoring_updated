from pydantic import BaseModel


class SafetyEventOut(BaseModel):
    id: str
    driverId: str
    vehicleId: str
    type: str
    severity: str
    confidence: float
    source: str
    timestamp: str
    snapshotUrl: str | None = None


class DriverMonitoringStatusOut(BaseModel):
    driverId: str
    vehicleId: str
    isOnline: bool
    presenceDetected: bool
    eyeState: str
    drowsinessLevel: str
    yawnStatus: str
    phoneUseStatus: str
    distractionStatus: str
    lastUpdated: str
    source: str
    metrics: dict[str, float] | None = None
    cameraStatus: str | None = None
    aiHealth: str | None = None
