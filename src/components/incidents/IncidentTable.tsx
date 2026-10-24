import { Table } from '@/components/ui/Table';
import type { TableColumn } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { severityTone, incidentStatusTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatDate';
import { Video } from 'lucide-react';
import type { Driver, Incident, Vehicle } from '@/types';

interface Props {
  incidents: Incident[];
  drivers: Driver[];
  vehicles: Vehicle[];
  onSelect: (incident: Incident) => void;
}

export function IncidentTable({ incidents, drivers, vehicles, onSelect }: Props) {
  const driverById = new Map(drivers.map((d) => [d.id, d]));
  const vehicleById = new Map(vehicles.map((v) => [v.id, v]));

  const columns: TableColumn<Incident>[] = [
    {
      key: 'type',
      header: 'Event',
      render: (i) => (
        <div className="flex items-center gap-1.5 font-medium text-text-primary">
          {i.evidenceId && (
            <span
              className="inline-flex items-center gap-1 text-[10px] bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.5 rounded font-semibold"
              title="Has MP4 Video Evidence"
            >
              <Video size={10} /> MP4
            </span>
          )}
          <span>{MONITORING_EVENT_LABELS[i.type] ?? i.type}</span>
        </div>
      ),
    },
    { key: 'driver', header: 'Driver', render: (i) => <span className="text-text-secondary">{driverById.get(i.driverId)?.name ?? i.driverId}</span> },
    { key: 'vehicle', header: 'Vehicle', render: (i) => <span className="text-text-secondary">{i.vehicleId ? vehicleById.get(i.vehicleId)?.plateNumber ?? i.vehicleId : '—'}</span> },
    { key: 'severity', header: 'Severity', render: (i) => <Badge label={i.severity} tone={severityTone(i.severity)} /> },
    { key: 'status', header: 'Status', render: (i) => <Badge label={i.status} tone={incidentStatusTone(i.status)} /> },
    { key: 'time', header: 'Time', render: (i) => <span className="text-text-secondary">{formatDateTime(i.timestamp)}</span> },
  ];

  return (
    <Table
      columns={columns}
      rows={incidents}
      getRowId={(i) => i.id}
      onRowClick={onSelect}
      emptyMessage="No incidents match your search or filters."
    />
  );
}
