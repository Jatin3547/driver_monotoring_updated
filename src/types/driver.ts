export type DriverStatus = 'active' | 'on-trip' | 'off-duty' | 'suspended';

export interface Driver {
  id: string;
  name: string;
  licenseNumber: string;
  phone: string;
  email: string;
  status: DriverStatus;
  safetyScore: number; // 0-100
  assignedVehicleId?: string;
  photoUrl?: string;
  joinedDate: string; // ISO date
  totalTrips: number;
  totalDistanceKm: number;
  incidentCount: number;
}
