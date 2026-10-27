import { useAsyncData } from '@/hooks/useAsyncData';
import { useAuth } from '@/hooks/useAuth';
import { getMyDriverProfile } from '@/services/api/driverService';
import { getMyTrips } from '@/services/api/tripService';
import { getMyIncidents } from '@/services/api/incidentService';
import { getAssignedVehicle } from '@/services/api/vehicleService';
import { getMyVehicleLocation } from '@/services/api/gpsService';
import { DriverProfilePanel } from '@/components/drivers/DriverProfilePanel';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, type TableColumn } from '@/components/ui/Table';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { formatDateTime } from '@/utils/formatDate';
import { incidentStatusTone, severityTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { USE_MOCK_DATA } from '@/services/config';
import type { Trip } from '@/types';

export default function DriverDashboardPage() {
  const { user } = useAuth();
  const { data: driver, status, error, refetch } = useAsyncData(() => getMyDriverProfile(), []);
  const { data: trips } = useAsyncData(() => getMyTrips(), []);
  const { data: incidents } = useAsyncData(() => getMyIncidents(), []);
  const { data: vehicle } = useAsyncData(() => getAssignedVehicle(), []);
  const { data: location, status: locationStatus } = useAsyncData(() => getMyVehicleLocation(), []);

  if (status === 'loading') return <LoadingState label="Loading your dashboard…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unable to load driver profile'} onRetry={refetch} />;
  if (!driver) return <ErrorState message="No driver profile is linked to this account." onRetry={refetch} />;

  const tripColumns: TableColumn<Trip>[] = [
    { key: 'when', header: 'Started', render: (row) => formatDateTime(row.startTime) },
    { key: 'route', header: 'Route', render: (row) => `${row.startLocation ?? '—'} → ${row.endLocation ?? '—'}` },
    { key: 'vehicle', header: 'Vehicle', render: (row) => row.vehiclePlate ?? row.vehicleCode ?? '—' },
    { key: 'distance', header: 'Distance', render: (row) => `${row.distanceKm ?? 0} km` },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge label={row.status} tone={row.status === 'in-progress' ? 'info' : 'neutral'} />,
    },
    { key: 'incidents', header: 'Incidents', render: (row) => String(row.incidentCount ?? 0) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm text-text-muted">Signed in as {user?.email}</h2>
        <p className="text-xs text-text-muted mt-0.5">
          {USE_MOCK_DATA ? 'Demo driver view' : 'Your trips, assigned vehicle, and safety record'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <DriverProfilePanel driver={driver} vehicle={vehicle ?? undefined} />
        </div>
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader title="My trips" subtitle={`${trips?.length ?? 0} recorded`} />
            <Table
              columns={tripColumns}
              rows={trips ?? []}
              getRowId={(row) => row.id}
              emptyMessage="No trips recorded for your account yet."
            />
          </Card>

          <Card>
            <CardHeader title="Assigned vehicle GPS" subtitle={location?.vehicleId ?? vehicle?.id ?? 'Current location'} />
            {location ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div><p className="text-xs text-text-muted">Latitude</p><p className="font-medium text-text-primary">{location.lat.toFixed(5)}</p></div>
                <div><p className="text-xs text-text-muted">Longitude</p><p className="font-medium text-text-primary">{location.lng.toFixed(5)}</p></div>
                <div><p className="text-xs text-text-muted">Speed</p><p className="font-medium text-text-primary">{Math.round(location.speedKmh)} km/h</p></div>
                <div><p className="text-xs text-text-muted">Updated</p><p className="font-medium text-text-primary">{formatDateTime(location.timestamp)}</p></div>
              </div>
            ) : (
              <p className="text-sm text-text-muted">
                {locationStatus === 'loading' ? 'Loading GPS position…' : 'No current GPS signal for your assigned vehicle.'}
              </p>
            )}
          </Card>

          <Card>
            <CardHeader title="My incidents" subtitle={`${incidents?.length ?? 0} recorded`} />
            {(incidents ?? []).length === 0 ? (
              <p className="text-sm text-text-muted">No incidents recorded for you.</p>
            ) : (
              <ul className="space-y-3">
                {(incidents ?? []).map((incident) => (
                  <li
                    key={incident.id}
                    className="flex items-center justify-between gap-3 pb-3 border-b border-border last:border-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary">
                        {MONITORING_EVENT_LABELS[incident.type] ?? incident.type}
                      </p>
                      <p className="text-xs text-text-muted">
                        {formatDateTime(incident.timestamp)} · {incident.location}
                      </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Badge label={incident.severity} tone={severityTone(incident.severity)} />
                      <Badge label={incident.status} tone={incidentStatusTone(incident.status)} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
