import { useMemo, useState } from 'react';
import { useVehicles } from '@/hooks/useVehicles';
import { useDrivers } from '@/hooks/useDrivers';
import { VehicleTable } from '@/components/vehicles/VehicleTable';
import { Card } from '@/components/ui/Card';
import { SearchInput } from '@/components/ui/SearchInput';
import { Select } from '@/components/ui/Select';
import { LoadingState, ErrorState } from '@/components/ui/States';

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'idle', label: 'Idle' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'offline', label: 'Offline' },
];

export default function VehiclesPage() {
  const { data: vehicles, status, error, refetch } = useVehicles();
  const { data: drivers } = useDrivers();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = useMemo(() => {
    if (!vehicles) return [];
    return vehicles.filter((v) => {
      const matchesQuery =
        query.trim() === '' ||
        v.plateNumber.toLowerCase().includes(query.toLowerCase()) ||
        v.model.toLowerCase().includes(query.toLowerCase()) ||
        v.id.toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === 'all' || v.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [vehicles, query, statusFilter]);

  if (status === 'loading') return <LoadingState label="Loading vehicles…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">All vehicles</h2>
          <p className="text-xs text-text-muted">{filtered.length} of {vehicles?.length ?? 0} vehicles</p>
        </div>
        <div className="flex gap-2">
          <SearchInput value={query} onChange={setQuery} placeholder="Search by plate, model or ID…" className="w-64" />
          <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
        </div>
      </div>

      <Card>
        <VehicleTable vehicles={filtered} drivers={drivers ?? []} />
      </Card>
    </div>
  );
}
