import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { severityTone } from '@/utils/statusColors';
import { formatDateTime } from '@/utils/formatDate';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import type { Driver, MonitoringEvent, Vehicle } from '@/types';
import { History } from 'lucide-react';

interface Props {
  events: MonitoringEvent[];
  drivers: Driver[];
  vehicles: Vehicle[];
}

export function EventTimeline({ events, drivers, vehicles }: Props) {
  const driverById = new Map(drivers.map((d) => [d.id, d]));
  const vehicleById = new Map(vehicles.map((v) => [v.id, v]));
  const sorted = [...events].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <Card>
      <CardHeader title="Recent detection events" subtitle="Chronological log from the monitoring service" />
      {sorted.length === 0 ? (
        <EmptyState icon={History} title="No events recorded" />
      ) : (
        <ol className="relative border-l border-border ml-2 space-y-5">
          {sorted.map((event, idx) => (
            <li key={`${event.id}-${idx}`} className="ml-4">
              <span className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-brand-blue mt-1.5" />
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-text-primary">
                  {MONITORING_EVENT_LABELS[event.type] ?? event.type}
                </span>
                <Badge label={event.severity} tone={severityTone(event.severity)} />
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                {driverById.get(event.driverId)?.name ?? event.driverId} · {vehicleById.get(event.vehicleId)?.plateNumber ?? event.vehicleId} ·{' '}
                {formatDateTime(event.timestamp)}
              </p>
              <p className="text-xs text-text-muted">Confidence: {Math.round(event.confidence * 100)}%</p>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
