import { useNavigate, useParams } from 'react-router-dom';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getDriverById } from '@/services/api/driverService';
import { getVehicles } from '@/services/api/vehicleService';
import { getIncidents } from '@/services/api/incidentService';
import { getMonitoringEvents } from '@/services/api/monitoringService';
import { DriverProfilePanel } from '@/components/drivers/DriverProfilePanel';
import { EventTimeline } from '@/components/monitoring/EventTimeline';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { severityTone, incidentStatusTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatDate';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, UserX } from 'lucide-react';

export default function DriverDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: driver, status, error, refetch } = useAsyncData(() => getDriverById(id!), [id]);
  const { data: vehicles } = useAsyncData(() => getVehicles(), []);
  const { data: incidents } = useAsyncData(() => getIncidents(), []);
  const { data: events } = useAsyncData(() => getMonitoringEvents(), []);

  if (status === 'loading') return <LoadingState label="Loading driver…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;
  if (!driver) {
    return (
      <EmptyState icon={UserX} title="Driver not found" description={`No driver matches ID "${id}".`} />
    );
  }

  const vehicle = vehicles?.find((v) => v.id === driver.assignedVehicleId);
  const driverIncidents = (incidents ?? []).filter((i) => i.driverId === driver.id);
  const driverEvents = (events ?? []).filter((e) => e.driverId === driver.id);

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => navigate('/drivers')} className="!px-0">
        <ArrowLeft size={14} /> Back to drivers
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <DriverProfilePanel driver={driver} vehicle={vehicle} />
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader title="Incident history" subtitle={`${driverIncidents.length} recorded incidents`} />
            {driverIncidents.length === 0 ? (
              <p className="text-sm text-text-muted">No incidents recorded for this driver.</p>
            ) : (
              <ul className="space-y-3">
                {driverIncidents.map((incident) => (
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

          <EventTimeline events={driverEvents} drivers={[driver]} vehicles={vehicles ?? []} />
        </div>
      </div>
    </div>
  );
}
