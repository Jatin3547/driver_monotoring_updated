from pydantic import BaseModel


class SafetyTrendPoint(BaseModel):
    date: str
    avgSafetyScore: float
    totalIncidents: int


class IncidentBreakdownSlice(BaseModel):
    type: str
    count: int


class DriverLeaderboardEntry(BaseModel):
    driverId: str
    driverName: str
    safetyScore: int
    incidentCount: int
    tripsCompleted: int


class FleetUtilizationPoint(BaseModel):
    date: str
    activeVehicles: int
    idleVehicles: int
    maintenanceVehicles: int


class FleetSummary(BaseModel):
    totalVehicles: int
    activeVehicles: int
    idleVehicles: int
    offlineVehicles: int
    maintenanceVehicles: int
    activeDrivers: int
    avgSafetyScore: float
    openIncidents: int
