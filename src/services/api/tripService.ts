import type { Trip } from '@/types';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export const mockTrips: Trip[] = [
  {
    id: 'TRP-1001',
    driverId: 'DRV-001',
    vehicleId: 'VEH-001',
    driverName: 'Arjun Mehta',
    driverCode: 'DRV-001',
    vehiclePlate: 'KA-01-AB-4521',
    vehicleCode: 'VEH-001',
    startTime: '2026-10-23T04:15:00Z',
    startLocation: 'Electronic City Hub',
    endLocation: 'Hebbal Logistics Center',
    distanceKm: 34.5,
    status: 'in-progress',
    incidentCount: 0,
  },
  {
    id: 'TRP-1002',
    driverId: 'DRV-005',
    vehicleId: 'VEH-005',
    driverName: 'Vikram Singh',
    driverCode: 'DRV-005',
    vehiclePlate: 'KA-09-IJ-6654',
    vehicleCode: 'VEH-005',
    startTime: '2026-10-23T02:30:00Z',
    startLocation: 'Outer Ring Road Hub',
    endLocation: 'Whitefield Depot',
    distanceKm: 52.0,
    status: 'in-progress',
    incidentCount: 2,
  },
  {
    id: 'TRP-1003',
    driverId: 'DRV-002',
    vehicleId: 'VEH-002',
    driverName: 'Priya Nair',
    driverCode: 'DRV-002',
    vehiclePlate: 'KA-03-CD-7812',
    vehicleCode: 'VEH-002',
    startTime: '2026-10-22T08:00:00Z',
    endTime: '2026-10-22T16:45:00Z',
    startLocation: 'Koramangala Hub',
    endLocation: 'Airport Cargo Terminal',
    distanceKm: 142.8,
    status: 'completed',
    incidentCount: 1,
  },
];

export async function getTrips(statusFilter?: string): Promise<Trip[]> {
  if (USE_MOCK_DATA) {
    let items = mockTrips;
    if (statusFilter) {
      items = items.filter((t) => t.status === statusFilter);
    }
    return mockDelay(items);
  }
  const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : '';
  return apiClient.get<Trip[]>(`/trips${query}`);
}

export async function getActiveTrips(): Promise<Trip[]> {
  if (USE_MOCK_DATA) {
    return mockDelay(mockTrips.filter((t) => t.status === 'in-progress'));
  }
  return apiClient.get<Trip[]>('/trips/active');
}

export async function getTripById(id: string): Promise<Trip | undefined> {
  if (USE_MOCK_DATA) {
    return mockDelay(mockTrips.find((t) => t.id === id));
  }
  return apiClient.get<Trip>(`/trips/${id}`);
}

export async function startTrip(driverCode: string, vehicleCode: string, startLocation: string, endLocation?: string): Promise<Trip> {
  if (USE_MOCK_DATA) {
    const newTrip: Trip = {
      id: `TRP-${Date.now().toString().slice(-4)}`,
      driverId: driverCode,
      vehicleId: vehicleCode,
      driverCode,
      vehicleCode,
      startTime: new Date().toISOString(),
      startLocation,
      endLocation,
      distanceKm: 0,
      status: 'in-progress',
      incidentCount: 0,
    };
    mockTrips.unshift(newTrip);
    return mockDelay(newTrip);
  }
  return apiClient.post<Trip>('/trips', {
    driverCode,
    vehicleCode,
    startLocation,
    endLocation,
  });
}
