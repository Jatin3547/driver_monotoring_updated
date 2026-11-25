import { useEffect, useRef, useState } from 'react';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getVehicleLocations } from '@/services/api/gpsService';
import { getVehicles } from '@/services/api/vehicleService';
import { getDrivers } from '@/services/api/driverService';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { FleetMap } from '@/components/map/FleetMap';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { timeAgo } from '@/utils/formatDate';
import { Gauge, Navigation, Radio } from 'lucide-react';
import { USE_MOCK_DATA } from '@/services/config';
import type { VehicleLocation } from '@/types';

function currentGPSStatus(location: VehicleLocation, now: number): string {
  const age = Math.max(0, (now - new Date(location.timestamp).getTime()) / 1000);
  if (age > location.staleAfterSeconds) return 'stale';
  return location.source === 'live' ? 'live' : 'simulated';
}

export default function GpsTrackingPage() {
  const { data: initialLocations, status, error, refetch } = useAsyncData(() => getVehicleLocations(), []);
  const { data: vehicles } = useAsyncData(() => getVehicles(), []);
  const { data: drivers } = useAsyncData(() => getDrivers(), []);

  // Live map: start from the REST snapshot, then patch individual vehicles
  // in place as gps_update events arrive over WebSocket. Falls back to
  // the static REST snapshot automatically in mock mode / while offline,
  // since useFleetSocketEvent is simply a no-op subscription then.
  const [liveLocations, setLiveLocations] = useState<VehicleLocation[] | null>(null);
  const [now, setNow] = useState(Date.now());
  const initialLocationsRef = useRef(initialLocations);
  useEffect(() => { initialLocationsRef.current = initialLocations; }, [initialLocations]);
  const locations = liveLocations ?? initialLocations ?? [];
  const displayedLocations = locations.map((location) => ({ ...location, gpsStatus: currentGPSStatus(location, now) }));

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 5000);
    return () => window.clearInterval(timer);
  }, []);

  useFleetSocketEvent<VehicleLocation>('gps_update', (update) => {
    setLiveLocations((prev) => {
      const base = prev ?? initialLocationsRef.current ?? [];
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
  const liveCount = locations.filter((location) => currentGPSStatus(location, now) === 'live').length;
  const simulatedCount = locations.filter((location) => currentGPSStatus(location, now) === 'simulated').length;
  const staleCount = locations.filter((location) => currentGPSStatus(location, now) === 'stale').length;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2">
        <Card padded={false} className="p-2">
          <div className="p-3 flex items-center justify-between">
            <CardHeader
              title="Fleet map"
              subtitle={`${liveCount} LIVE GPS · ${simulatedCount} SIMULATED · ${staleCount} STALE`}
            />
            <span className={`flex items-center gap-1 text-xs shrink-0 ${USE_MOCK_DATA ? 'text-blue-600' : 'text-status-success-text'}`}>
              <Radio size={12} /> {USE_MOCK_DATA ? 'DEMO DATA' : 'WebSocket'}
            </span>
          </div>
          <FleetMap locations={displayedLocations} vehicles={vehicles ?? []} drivers={drivers ?? []} height="560px" />
        </Card>
      </div>

      <Card>
        <CardHeader title="Vehicle locations" subtitle={`${locations.length} positions · freshness updates every 5 seconds`} />
        <ul className="space-y-3 max-h-[520px] overflow-y-auto">
          {locations.map((loc) => {
            const vehicle = vehicleById.get(loc.vehicleId);
            const driver = vehicle?.assignedDriverId ? driverById.get(vehicle.assignedDriverId) : undefined;
            if (!vehicle) return null;
            const gpsStatus = currentGPSStatus(loc, now);
            return (
              <li key={loc.vehicleId} className="pb-3 border-b border-border last:border-0 last:pb-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-text-primary">{vehicle.plateNumber}</span>
                  <Badge label={gpsStatus === 'live' ? 'LIVE GPS' : gpsStatus === 'stale' ? `STALE ${loc.source === 'live' ? 'LIVE GPS' : 'SIMULATED GPS'}` : 'SIMULATED GPS'} tone={gpsStatus === 'live' ? 'success' : gpsStatus === 'stale' ? 'warning' : 'info'} />
                </div>
                <p className="text-xs text-text-muted mb-1">{driver ? driver.name : 'Unassigned'}</p>
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  <span className="flex items-center gap-1"><Gauge size={12} /> {loc.speedKmh == null ? '—' : `${loc.speedKmh} km/h`}</span>
                  <span className="flex items-center gap-1"><Navigation size={12} /> {loc.heading == null ? '—' : `${loc.heading}°`}</span>
                  <span className="text-text-muted">{timeAgo(loc.timestamp)}</span>
                  <span className="text-text-muted">{loc.accuracyM == null ? 'Accuracy n/a' : `±${Math.round(loc.accuracyM)} m`}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
