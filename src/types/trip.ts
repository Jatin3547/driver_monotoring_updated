export interface Trip {
  id: string;
  vehicleId: string;
  driverId: string;
  startTime: string; // ISO datetime
  endTime?: string | null;
  startLocation?: string | null;
  endLocation?: string | null;
  distanceKm: number;
  status: 'in-progress' | 'completed' | 'cancelled';
  driverName?: string | null;
  driverCode?: string | null;
  vehiclePlate?: string | null;
  vehicleCode?: string | null;
  incidentCount?: number;
}
