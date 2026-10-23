import { useNavigate } from 'react-router-dom';
import { Table } from '@/components/ui/Table';
import type { TableColumn } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { vehicleStatusTone } from '@/utils/statusColors';
import { VEHICLE_TYPE_LABELS } from '@/utils/constants';
import { formatNumber } from '@/utils/formatDate';
import type { Driver, Vehicle } from '@/types';

export function VehicleTable({ vehicles, drivers }: { vehicles: Vehicle[]; drivers: Driver[] }) {
  const navigate = useNavigate();
  const driverById = new Map(drivers.map((d) => [d.id, d]));

  const columns: TableColumn<Vehicle>[] = [
    {
      key: 'plate',
      header: 'Vehicle',
      render: (v) => (
        <div>
          <p className="font-medium text-text-primary leading-tight">{v.plateNumber}</p>
          <p className="text-xs text-text-muted">{v.make} {v.model} · {v.year}</p>
        </div>
      ),
    },
    { key: 'type', header: 'Type', render: (v) => <span className="text-text-secondary">{VEHICLE_TYPE_LABELS[v.type]}</span> },
    {
      key: 'driver',
      header: 'Assigned driver',
      render: (v) => <span className="text-text-secondary">{v.assignedDriverId ? driverById.get(v.assignedDriverId)?.name ?? v.assignedDriverId : 'Unassigned'}</span>,
    },
    { key: 'status', header: 'Status', render: (v) => <Badge label={v.status} tone={vehicleStatusTone(v.status)} /> },
    { key: 'odometer', header: 'Odometer', render: (v) => <span className="text-text-secondary">{formatNumber(v.odometerKm)} km</span> },
    {
      key: 'fuel',
      header: 'Fuel',
      render: (v) => (
        <div className="flex items-center gap-2 w-24">
          <div className="flex-1 h-1.5 rounded-full bg-surface-inset overflow-hidden">
            <div
              className={`h-full ${v.fuelLevel > 30 ? 'bg-status-success-text' : 'bg-status-danger-text'}`}
              style={{ width: `${v.fuelLevel}%` }}
            />
          </div>
          <span className="text-xs text-text-muted w-8 text-right">{v.fuelLevel}%</span>
        </div>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      rows={vehicles}
      getRowId={(v) => v.id}
      onRowClick={(v) => navigate(`/vehicles/${v.id}`)}
      emptyMessage="No vehicles match your search or filters."
    />
  );
}
