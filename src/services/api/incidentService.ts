import type { Alert, Incident } from '@/types';
import { mockIncidents, mockAlerts } from '@/mock/incidents.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getIncidents(): Promise<Incident[]> {
  if (USE_MOCK_DATA) return mockDelay(mockIncidents);
  return apiClient.get<Incident[]>('/incidents');
}

export async function getAlerts(): Promise<Alert[]> {
  if (USE_MOCK_DATA) return mockDelay(mockAlerts);
  return apiClient.get<Alert[]>('/alerts');
}

export async function updateIncidentStatus(
  incidentId: string,
  status: 'open' | 'reviewed' | 'resolved',
  acknowledgedBy?: string
): Promise<Incident> {
  if (USE_MOCK_DATA) {
    const item = mockIncidents.find((i) => i.id === incidentId);
    if (item) {
      item.status = status;
    }
    return mockDelay(item ?? ({} as Incident));
  }
  return apiClient.patch<Incident>(`/incidents/${incidentId}`, {
    status,
    acknowledgedBy,
  });
}

