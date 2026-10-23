import type { Vehicle } from '@/types';
import { mockVehicles } from '@/mock/vehicles.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getVehicles(): Promise<Vehicle[]> {
  if (USE_MOCK_DATA) return mockDelay(mockVehicles);
  return apiClient.get<Vehicle[]>('/vehicles');
}

export async function getVehicleById(id: string): Promise<Vehicle | undefined> {
  if (USE_MOCK_DATA) return mockDelay(mockVehicles.find((v) => v.id === id));
  return apiClient.get<Vehicle>(`/vehicles/${id}`);
}
