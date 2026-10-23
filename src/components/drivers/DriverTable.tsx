import { useNavigate } from 'react-router-dom';
import { Table } from '@/components/ui/Table';
import type { TableColumn } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { driverStatusTone } from '@/utils/statusColors';
import type { Driver } from '@/types';

export function DriverTable({ drivers }: { drivers: Driver[] }) {
  const navigate = useNavigate();

  const columns: TableColumn<Driver>[] = [
    {
      key: 'name',
      header: 'Driver',
      render: (d) => (
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-full bg-status-info-bg text-status-info-text flex items-center justify-center text-xs font-semibold shrink-0">
            {d.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
          </span>
          <div>
            <p className="font-medium text-text-primary leading-tight">{d.name}</p>
            <p className="text-xs text-text-muted">{d.id}</p>
          </div>
        </div>
      ),
    },
    { key: 'license', header: 'License No.', render: (d) => <span className="text-text-secondary">{d.licenseNumber}</span> },
    { key: 'vehicle', header: 'Vehicle', render: (d) => <span className="text-text-secondary">{d.assignedVehicleId ?? '—'}</span> },
    { key: 'status', header: 'Status', render: (d) => <Badge label={d.status.replace('-', ' ')} tone={driverStatusTone(d.status)} /> },
    {
      key: 'score',
      header: 'Safety score',
      render: (d) => (
        <span
          className={
            d.safetyScore >= 80
              ? 'text-status-success-text font-semibold'
              : d.safetyScore >= 60
                ? 'text-status-warning-text font-semibold'
                : 'text-status-danger-text font-semibold'
          }
        >
          {d.safetyScore}
        </span>
      ),
    },
    { key: 'incidents', header: 'Incidents', render: (d) => <span className="text-text-secondary">{d.incidentCount}</span> },
  ];

  return (
    <Table
      columns={columns}
      rows={drivers}
      getRowId={(d) => d.id}
      onRowClick={(d) => navigate(`/drivers/${d.id}`)}
      emptyMessage="No drivers match your search or filters."
    />
  );
}
