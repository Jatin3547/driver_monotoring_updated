import { getVehicles } from '@/services/api/vehicleService';
import { useAsyncData } from './useAsyncData';

export function useVehicles() {
  return useAsyncData(() => getVehicles(), []);
}
