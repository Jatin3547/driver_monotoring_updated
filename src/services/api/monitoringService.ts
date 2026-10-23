import type { DriverMonitoringStatus, MonitoringEvent } from '@/types';
import { mockMonitoringStatuses, mockMonitoringEvents } from '@/mock/monitoring.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getMonitoringStatuses(): Promise<DriverMonitoringStatus[]> {
  if (USE_MOCK_DATA) return mockDelay(mockMonitoringStatuses);
  return apiClient.get<DriverMonitoringStatus[]>('/monitoring/status');
}

export interface AiStatus {
  configuredMode: string;
  activeSource: 'simulation' | 'live';
  visionDependenciesInstalled: boolean;
  cameraIndex: number;
}

export async function getAiStatus(): Promise<AiStatus> {
  if (USE_MOCK_DATA) {
    return mockDelay({
      configuredMode: 'demo',
      activeSource: 'simulation',
      visionDependenciesInstalled: false,
      cameraIndex: 0,
    });
  }
  return apiClient.get<AiStatus>('/monitoring/ai-status');
}

export async function getMonitoringEvents(): Promise<MonitoringEvent[]> {
  if (USE_MOCK_DATA) return mockDelay(mockMonitoringEvents);
  return apiClient.get<MonitoringEvent[]>('/monitoring/events');
}
