export interface FleetSafetyTrendPoint {
  date: string; // ISO date
  avgSafetyScore: number;
  totalIncidents: number;
}

export interface IncidentBreakdownSlice {
  type: string;
  count: number;
}

export interface DriverLeaderboardEntry {
  driverId: string;
  driverName: string;
  safetyScore: number;
  incidentCount: number;
  tripsCompleted: number;
}

export interface FleetUtilizationPoint {
  date: string;
  activeVehicles: number;
  idleVehicles: number;
  maintenanceVehicles: number;
}
