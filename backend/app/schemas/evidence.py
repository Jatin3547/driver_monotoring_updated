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
    status: str
    errorMessage: str | None = None
    sha256Hash: str | None = None
    cloudUploadStatus: str = "pending"
    createdAt: str
    eventTimestamp: str | None = None
    downloadUrl: str
    streamUrl: str | None = None
    snapshotUrl: str | None = None


class EvidenceCreate(BaseModel):
    incidentId: str
    safetyEventId: str | None = None
    driverId: str
    vehicleId: str
    tripId: str | None = None
    filePath: str
    fileType: str = "video/mp4"
    fileSizeBytes: int = 0
    durationSeconds: float = 15.0
    preEventSeconds: float = 5.0
    postEventSeconds: float = 10.0
    retentionDays: int = 7
    isProtected: bool = False
    status: str = "available"
    errorMessage: str | None = None
    sha256Hash: str | None = None
    snapshotPath: str | None = None
    cloudUploadStatus: str = "pending"


class EvidenceProtectUpdate(BaseModel):
    isProtected: bool


class EvidenceHashVerifyOut(BaseModel):
    evidenceId: str
    matches: bool
    storedHash: str | None
    computedHash: str | None
    details: str
