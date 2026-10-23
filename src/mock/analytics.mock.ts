import type {
  DriverLeaderboardEntry,
  FleetSafetyTrendPoint,
  FleetUtilizationPoint,
  IncidentBreakdownSlice,
} from '@/types';

export const mockSafetyTrend: FleetSafetyTrendPoint[] = [
  { date: '2026-09-01', avgSafetyScore: 79, totalIncidents: 6 },
  { date: '2026-09-04', avgSafetyScore: 81, totalIncidents: 4 },
  { date: '2026-09-07', avgSafetyScore: 80, totalIncidents: 5 },
  { date: '2026-09-10', avgSafetyScore: 77, totalIncidents: 8 },
  { date: '2026-09-13', avgSafetyScore: 82, totalIncidents: 3 },
  { date: '2026-09-16', avgSafetyScore: 84, totalIncidents: 2 },
  { date: '2026-09-19', avgSafetyScore: 83, totalIncidents: 4 },
  { date: '2026-09-22', avgSafetyScore: 79, totalIncidents: 7 },
  { date: '2026-09-25', avgSafetyScore: 78, totalIncidents: 9 },
];

export const mockIncidentBreakdown: IncidentBreakdownSlice[] = [
  { type: 'Drowsiness', count: 14 },
  { type: 'Phone use', count: 9 },
  { type: 'Yawning', count: 11 },
  { type: 'Distraction', count: 7 },
  { type: 'Speeding', count: 6 },
  { type: 'Harsh braking', count: 5 },
];

export const mockDriverLeaderboard: DriverLeaderboardEntry[] = [
  { driverId: 'DRV-004', driverName: 'Sneha Reddy', safetyScore: 95, incidentCount: 0, tripsCompleted: 512 },
  { driverId: 'DRV-001', driverName: 'Arjun Mehta', safetyScore: 92, incidentCount: 1, tripsCompleted: 842 },
  { driverId: 'DRV-006', driverName: 'Anita Desai', safetyScore: 90, incidentCount: 1, tripsCompleted: 298 },
  { driverId: 'DRV-003', driverName: 'Rohit Sharma', safetyScore: 88, incidentCount: 3, tripsCompleted: 2310 },
  { driverId: 'DRV-008', driverName: 'Meera Iyer', safetyScore: 85, incidentCount: 2, tripsCompleted: 967 },
  { driverId: 'DRV-002', driverName: 'Priya Nair', safetyScore: 78, incidentCount: 5, tripsCompleted: 1204 },
  { driverId: 'DRV-009', driverName: 'Suresh Kumar', safetyScore: 73, incidentCount: 8, tripsCompleted: 4021 },
  { driverId: 'DRV-005', driverName: 'Vikram Singh', safetyScore: 64, incidentCount: 11, tripsCompleted: 3140 },
  { driverId: 'DRV-007', driverName: 'Karan Malhotra', safetyScore: 42, incidentCount: 19, tripsCompleted: 1876 },
];

export const mockFleetUtilization: FleetUtilizationPoint[] = [
  { date: '2026-09-19', activeVehicles: 6, idleVehicles: 2, maintenanceVehicles: 1 },
  { date: '2026-09-20', activeVehicles: 7, idleVehicles: 1, maintenanceVehicles: 1 },
  { date: '2026-09-21', activeVehicles: 5, idleVehicles: 3, maintenanceVehicles: 1 },
  { date: '2026-09-22', activeVehicles: 7, idleVehicles: 1, maintenanceVehicles: 1 },
  { date: '2026-09-23', activeVehicles: 6, idleVehicles: 2, maintenanceVehicles: 1 },
  { date: '2026-09-24', activeVehicles: 7, idleVehicles: 1, maintenanceVehicles: 1 },
  { date: '2026-09-25', activeVehicles: 6, idleVehicles: 2, maintenanceVehicles: 1 },
];
