import type {
  DriverLeaderboardEntry,
  FleetSafetyTrendPoint,
  FleetUtilizationPoint,
  IncidentBreakdownSlice,
} from '@/types';
import {
  mockSafetyTrend,
  mockIncidentBreakdown,
  mockDriverLeaderboard,
  mockFleetUtilization,
} from '@/mock/analytics.mock';
import { USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';

export async function getSafetyTrend(): Promise<FleetSafetyTrendPoint[]> {
  if (USE_MOCK_DATA) return mockDelay(mockSafetyTrend);
  return apiClient.get<FleetSafetyTrendPoint[]>('/analytics/safety-trend');
}

export async function getIncidentBreakdown(): Promise<IncidentBreakdownSlice[]> {
  if (USE_MOCK_DATA) return mockDelay(mockIncidentBreakdown);
  return apiClient.get<IncidentBreakdownSlice[]>('/analytics/incident-breakdown');
}

export async function getDriverLeaderboard(): Promise<DriverLeaderboardEntry[]> {
  if (USE_MOCK_DATA) return mockDelay(mockDriverLeaderboard);
  return apiClient.get<DriverLeaderboardEntry[]>('/analytics/driver-leaderboard');
}

export async function getFleetUtilization(): Promise<FleetUtilizationPoint[]> {
  if (USE_MOCK_DATA) return mockDelay(mockFleetUtilization);
  return apiClient.get<FleetUtilizationPoint[]>('/analytics/fleet-utilization');
}
