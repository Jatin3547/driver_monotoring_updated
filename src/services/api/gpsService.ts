import type { DriverGPSConfig, DriverGPSUpdate, DriverGPSUpdateResult, VehicleLocation } from '@/types';
import { mockVehicleLocations } from '@/mock/gps.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getVehicleLocations(): Promise<VehicleLocation[]> {
  if (USE_MOCK_DATA) return mockDelay(mockVehicleLocations);
  return apiClient.get<VehicleLocation[]>('/gps/locations');
}

export async function getMyVehicleLocation(): Promise<VehicleLocation | undefined> {
  if (USE_MOCK_DATA) return mockDelay(mockVehicleLocations[0]);
  try {
    return await apiClient.get<VehicleLocation>('/gps/my-vehicle');
  } catch (error) {
    if (error instanceof Error && error.message.includes('404')) return undefined;
    throw error;
  }
}

export function updateMyGPSLocation(update: DriverGPSUpdate): Promise<DriverGPSUpdateResult> {
  return apiClient.post<DriverGPSUpdateResult>('/gps/my-location', update);
}

export function getDriverGPSConfig(): Promise<DriverGPSConfig> {
  return apiClient.get<DriverGPSConfig>('/gps/config');
}
