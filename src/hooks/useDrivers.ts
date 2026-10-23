import { getDrivers } from '@/services/api/driverService';
import { useAsyncData } from './useAsyncData';

export function useDrivers() {
  return useAsyncData(() => getDrivers(), []);
}
