import type { Driver } from '@/types';
import { mockDrivers } from '@/mock/drivers.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getDrivers(): Promise<Driver[]> {
  if (USE_MOCK_DATA) return mockDelay(mockDrivers);
  return apiClient.get<Driver[]>('/drivers');
}

export async function getDriverById(id: string): Promise<Driver | undefined> {
  if (USE_MOCK_DATA) return mockDelay(mockDrivers.find((d) => d.id === id));
  return apiClient.get<Driver>(`/drivers/${id}`);
}
