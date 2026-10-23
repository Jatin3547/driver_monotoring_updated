import type { VehicleLocation } from '@/types';
import { mockVehicleLocations } from '@/mock/gps.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getVehicleLocations(): Promise<VehicleLocation[]> {
  if (USE_MOCK_DATA) return mockDelay(mockVehicleLocations);
  return apiClient.get<VehicleLocation[]>('/gps/locations');
}
