import type { DriverMonitoringStatus, MonitoringEvent } from '@/types';
import { mockMonitoringStatuses, mockMonitoringEvents } from '@/mock/monitoring.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getMonitoringStatuses(): Promise<DriverMonitoringStatus[]> {
  if (USE_MOCK_DATA) return mockDelay(mockMonitoringStatuses);
  return apiClient.get<DriverMonitoringStatus[]>('/monitoring/status');
}

/** Monitoring snapshot scoped to the authenticated driver account. */
export async function getMyMonitoringStatus(driverCode?: string): Promise<DriverMonitoringStatus | undefined> {
  if (USE_MOCK_DATA) {
    return mockDelay(mockMonitoringStatuses.find((item) => !driverCode || item.driverId === driverCode));
  }
  try {
    return await apiClient.get<DriverMonitoringStatus>('/monitoring/my-status');
  } catch (error) {
    if (error instanceof Error && error.message.includes('404')) return undefined;
    throw error;
  }
}

export interface AiStatus {
  configuredMode: string;
  activeSource: 'simulation' | 'live' | 'browser_live' | 'unavailable';
  visionDependenciesInstalled: boolean;
  cameraIndex: number;
  openCvAvailable?: boolean;
  mediaPipeAvailable?: boolean;
  phoneDetectorAvailable?: boolean;
  cameraAvailable?: boolean;
  cameraStatus?: string;
  monitoringState?: string;
  currentDriverState?: Record<string, unknown> | null;
  error?: string | null;
  browserSessions?: BrowserCameraSession[];
  diagnostics?: Record<string, unknown>;
}

export interface BrowserCameraSession {
  driverId: string;
  vehicleId: string;
  startedAt: string;
  lastFrameAt: string | null;
  status: 'connecting' | 'active';
  aiHealth: 'starting' | 'healthy' | 'degraded';
  framesProcessed?: number;
  processingLatencyMs?: number | null;
  signals?: Record<string, string | boolean | null>;
}

export async function getBrowserCameraSessions(): Promise<BrowserCameraSession[]> {
  if (USE_MOCK_DATA) return mockDelay([]);
  return apiClient.get<BrowserCameraSession[]>('/monitoring/browser-sessions');
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
