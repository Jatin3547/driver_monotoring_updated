import { useNavigate, useParams } from 'react-router-dom';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getVehicleById } from '@/services/api/vehicleService';
import { getDrivers } from '@/services/api/driverService';
import { getIncidents } from '@/services/api/incidentService';
import { getVehicleLocations } from '@/services/api/gpsService';
import { VehicleInfoPanel } from '@/components/vehicles/VehicleInfoPanel';
import { FleetMap } from '@/components/map/FleetMap';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { severityTone, incidentStatusTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatDate';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, TruckIcon } from 'lucide-react';

export default function VehicleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: vehicle, status, error, refetch } = useAsyncData(() => getVehicleById(id!), [id]);
  const { data: drivers } = useAsyncData(() => getDrivers(), []);
  const { data: incidents } = useAsyncData(() => getIncidents(), []);
  const { data: locations } = useAsyncData(() => getVehicleLocations(), []);

  if (status === 'loading') return <LoadingState label="Loading vehicle…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;
  if (!vehicle) {
    return <EmptyState icon={TruckIcon} title="Vehicle not found" description={`No vehicle matches ID "${id}".`} />;
  }

  const driver = drivers?.find((d) => d.id === vehicle.assignedDriverId);
  const vehicleIncidents = (incidents ?? []).filter((i) => i.vehicleId === vehicle.id);
  const location = locations?.find((l) => l.vehicleId === vehicle.id);

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => navigate('/vehicles')} className="!px-0">
        <ArrowLeft size={14} /> Back to vehicles
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <VehicleInfoPanel vehicle={vehicle} driver={driver} />
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader title="Current location" subtitle={location ? `${location.speedKmh} km/h` : 'No live signal'} />
            {location ? (
              <FleetMap locations={[location]} vehicles={[vehicle]} drivers={drivers ?? []} height="320px" />
            ) : (
              <p className="text-sm text-text-muted">This vehicle has no live GPS signal.</p>
            )}
          </Card>

          <Card>
            <CardHeader title="Incident history" subtitle={`${vehicleIncidents.length} recorded incidents`} />
            {vehicleIncidents.length === 0 ? (
              <p className="text-sm text-text-muted">No incidents recorded for this vehicle.</p>
            ) : (
              <ul className="space-y-3">
                {vehicleIncidents.map((incident) => (
                  <li key={incident.id} className="flex items-center justify-between gap-3 pb-3 border-b border-border last:border-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary">{MONITORING_EVENT_LABELS[incident.type] ?? incident.type}</p>
                      <p className="text-xs text-text-muted">{formatDateTime(incident.timestamp)} · {incident.location}</p>
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
