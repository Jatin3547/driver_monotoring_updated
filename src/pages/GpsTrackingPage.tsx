import { useState } from 'react';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getVehicleLocations } from '@/services/api/gpsService';
import { getVehicles } from '@/services/api/vehicleService';
import { getDrivers } from '@/services/api/driverService';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { FleetMap } from '@/components/map/FleetMap';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { vehicleStatusTone } from '@/utils/statusColors';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { timeAgo } from '@/utils/formatDate';
import { Gauge, Navigation, Radio } from 'lucide-react';
import { USE_MOCK_DATA } from '@/services/config';
import type { VehicleLocation } from '@/types';

export default function GpsTrackingPage() {
  const { data: initialLocations, status, error, refetch } = useAsyncData(() => getVehicleLocations(), []);
  const { data: vehicles } = useAsyncData(() => getVehicles(), []);
  const { data: drivers } = useAsyncData(() => getDrivers(), []);

  // Live map: start from the REST snapshot, then patch individual vehicles
  // in place as gps_update events arrive over WebSocket. Falls back to
  // the static REST snapshot automatically in mock mode / while offline,
  // since useFleetSocketEvent is simply a no-op subscription then.
  const [liveLocations, setLiveLocations] = useState<VehicleLocation[] | null>(null);
  const locations = liveLocations ?? initialLocations ?? [];

  useFleetSocketEvent<VehicleLocation>('gps_update', (update) => {
    setLiveLocations((prev) => {
      const base = prev ?? initialLocations ?? [];
      const exists = base.some((l) => l.vehicleId === update.vehicleId);
      return exists
        ? base.map((l) => (l.vehicleId === update.vehicleId ? update : l))
        : [...base, update];
    });
  });

  if (status === 'loading') return <LoadingState label="Fetching live positions…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  const vehicleById = new Map((vehicles ?? []).map((v) => [v.id, v]));
  const driverById = new Map((drivers ?? []).map((d) => [d.id, d]));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2">
        <Card padded={false} className="p-2">
          <div className="p-3 flex items-center justify-between">
            <CardHeader
              title="Fleet map"
              subtitle={
                USE_MOCK_DATA
                  ? 'Simulated GPS positions (demo mode)'
                  : 'Simulated GPS positions, updating live over WebSocket'
              }
            />
            {!USE_MOCK_DATA && (
              <span className="flex items-center gap-1 text-xs text-status-success-text shrink-0">
                <Radio size={12} /> live
              </span>
            )}
          </div>
          <FleetMap locations={locations} vehicles={vehicles ?? []} drivers={drivers ?? []} height="560px" />
        </Card>
      </div>

      <Card>
        <CardHeader title="Vehicles in transit" subtitle={`${locations.length} reporting a live position`} />
        <ul className="space-y-3 max-h-[520px] overflow-y-auto">
          {locations.map((loc) => {
            const vehicle = vehicleById.get(loc.vehicleId);
            const driver = vehicle?.assignedDriverId ? driverById.get(vehicle.assignedDriverId) : undefined;
            if (!vehicle) return null;
            return (
              <li key={loc.vehicleId} className="pb-3 border-b border-border last:border-0 last:pb-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-text-primary">{vehicle.plateNumber}</span>
                  <Badge label={vehicle.status} tone={vehicleStatusTone(vehicle.status)} />
                </div>
                <p className="text-xs text-text-muted mb-1">{driver ? driver.name : 'Unassigned'}</p>
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  <span className="flex items-center gap-1"><Gauge size={12} /> {loc.speedKmh} km/h</span>
                  <span className="flex items-center gap-1"><Navigation size={12} /> {loc.heading}°</span>
                  <span className="text-text-muted">{timeAgo(loc.timestamp)}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
