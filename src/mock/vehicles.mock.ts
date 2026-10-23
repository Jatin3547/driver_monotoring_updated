import type { Vehicle } from '@/types';

export const mockVehicles: Vehicle[] = [
  { id: 'VEH-001', plateNumber: 'KA-01-AB-4521', model: 'Pro 6035', make: 'Tata', year: 2022, type: 'truck', status: 'active', assignedDriverId: 'DRV-001', odometerKm: 118420, fuelLevel: 72, lastServiceDate: '2026-07-15', nextServiceDueKm: 130000 },
  { id: 'VEH-002', plateNumber: 'KA-03-CD-7812', model: 'Traveller', make: 'Force', year: 2021, type: 'van', status: 'active', assignedDriverId: 'DRV-002', odometerKm: 203110, fuelLevel: 45, lastServiceDate: '2026-06-02', nextServiceDueKm: 210000 },
  { id: 'VEH-003', plateNumber: 'KA-05-EF-3390', model: 'Signature', make: 'Ashok Leyland', year: 2019, type: 'truck', status: 'active', assignedDriverId: 'DRV-003', odometerKm: 402330, fuelLevel: 61, lastServiceDate: '2026-08-20', nextServiceDueKm: 410000 },
  { id: 'VEH-004', plateNumber: 'KA-02-GH-1123', model: 'Winger', make: 'Tata', year: 2023, type: 'van', status: 'idle', assignedDriverId: 'DRV-004', odometerKm: 76210, fuelLevel: 88, lastServiceDate: '2026-09-01', nextServiceDueKm: 90000 },
  { id: 'VEH-005', plateNumber: 'KA-09-IJ-6654', model: '407 Pickup', make: 'Tata', year: 2018, type: 'truck', status: 'active', assignedDriverId: 'DRV-005', odometerKm: 588400, fuelLevel: 33, lastServiceDate: '2026-05-11', nextServiceDueKm: 595000 },
  { id: 'VEH-006', plateNumber: 'KA-04-KL-9087', model: 'Starbus', make: 'Ashok Leyland', year: 2023, type: 'bus', status: 'active', assignedDriverId: 'DRV-006', odometerKm: 41200, fuelLevel: 55, lastServiceDate: '2026-08-30', nextServiceDueKm: 50000 },
  { id: 'VEH-007', plateNumber: 'KA-07-MN-2245', model: 'City', make: 'Honda', year: 2021, type: 'car', status: 'active', assignedDriverId: 'DRV-008', odometerKm: 154880, fuelLevel: 67, lastServiceDate: '2026-07-28', nextServiceDueKm: 160000 },
  { id: 'VEH-008', plateNumber: 'KA-08-OP-5578', model: 'Bolero Pickup', make: 'Mahindra', year: 2017, type: 'truck', status: 'maintenance', assignedDriverId: 'DRV-009', odometerKm: 712300, fuelLevel: 12, lastServiceDate: '2026-09-20', nextServiceDueKm: 715000 },
  { id: 'VEH-009', plateNumber: 'KA-06-QR-8834', model: 'Cruiser', make: 'Toyota', year: 2020, type: 'van', status: 'offline', assignedDriverId: undefined, odometerKm: 267500, fuelLevel: 0, lastServiceDate: '2026-04-10', nextServiceDueKm: 275000 },
];
