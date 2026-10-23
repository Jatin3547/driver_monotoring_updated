import type { VehicleLocation } from '@/types';

// Bengaluru-centered coordinates, one point per active/idle vehicle.
// Offline vehicles (VEH-009) intentionally have no live location.
export const mockVehicleLocations: VehicleLocation[] = [
  { vehicleId: 'VEH-001', lat: 12.9716, lng: 77.5946, speedKmh: 42, heading: 88, accelerationMs2: 0.4, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-002', lat: 12.9352, lng: 77.6245, speedKmh: 0, heading: 0, accelerationMs2: 0, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-003', lat: 13.0067, lng: 77.5673, speedKmh: 61, heading: 172, accelerationMs2: -1.8, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-004', lat: 12.9141, lng: 77.6386, speedKmh: 0, heading: 0, accelerationMs2: 0, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-005', lat: 12.9784, lng: 77.6408, speedKmh: 78, heading: 210, accelerationMs2: 2.4, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-006', lat: 12.9539, lng: 77.4922, speedKmh: 35, heading: 300, accelerationMs2: 0.1, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-007', lat: 12.9101, lng: 77.5488, speedKmh: 29, heading: 65, accelerationMs2: -0.3, timestamp: '2026-09-25T09:12:00Z' },
  { vehicleId: 'VEH-008', lat: 13.0298, lng: 77.5619, speedKmh: 0, heading: 0, accelerationMs2: 0, timestamp: '2026-09-25T09:12:00Z' },
];
