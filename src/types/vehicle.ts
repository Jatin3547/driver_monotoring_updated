export type VehicleStatus = 'active' | 'idle' | 'maintenance' | 'offline';
export type VehicleType = 'truck' | 'van' | 'car' | 'bus';

export interface Vehicle {
  id: string;
  plateNumber: string;
  model: string;
  make: string;
  year: number;
  type: VehicleType;
  status: VehicleStatus;
  assignedDriverId?: string;
  odometerKm: number;
  fuelLevel: number; // 0-100
  lastServiceDate: string; // ISO date
  nextServiceDueKm: number;
}
