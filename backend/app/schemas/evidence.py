from pydantic import BaseModel


class EvidenceOut(BaseModel):
    id: str
    incidentId: str
    safetyEventId: str | None = None
    driverId: str
    vehicleId: str
    tripId: str | None = None
    fileType: str
    fileSizeBytes: int
    durationSeconds: float | None = None
    preEventSeconds: float
    postEventSeconds: float
    retentionDays: int
    isProtected: bool
    createdAt: str
    downloadUrl: str


class EvidenceCreate(BaseModel):
    incidentId: str
    safetyEventId: str | None = None
    driverId: str
    vehicleId: str
    tripId: str | None = None
    filePath: str
    fileType: str = "video/mp4"
    fileSizeBytes: int = 0
    durationSeconds: float = 8.0
    preEventSeconds: float = 5.0
    postEventSeconds: float = 3.0
    isProtected: bool = False


class EvidenceProtectUpdate(BaseModel):
    isProtected: bool
