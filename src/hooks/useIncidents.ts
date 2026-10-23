import { getIncidents } from '@/services/api/incidentService';
import { useAsyncData } from './useAsyncData';

export function useIncidents() {
  return useAsyncData(() => getIncidents(), []);
}
