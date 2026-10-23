import { useMemo, useState } from 'react';
import { useDrivers } from '@/hooks/useDrivers';
import { DriverTable } from '@/components/drivers/DriverTable';
import { Card } from '@/components/ui/Card';
import { SearchInput } from '@/components/ui/SearchInput';
import { Select } from '@/components/ui/Select';
import { LoadingState, ErrorState } from '@/components/ui/States';

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'on-trip', label: 'On trip' },
  { value: 'off-duty', label: 'Off duty' },
  { value: 'suspended', label: 'Suspended' },
];

export default function DriversPage() {
  const { data: drivers, status, error, refetch } = useDrivers();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = useMemo(() => {
    if (!drivers) return [];
    return drivers.filter((d) => {
      const matchesQuery =
        query.trim() === '' ||
        d.name.toLowerCase().includes(query.toLowerCase()) ||
        d.licenseNumber.toLowerCase().includes(query.toLowerCase()) ||
        d.id.toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [drivers, query, statusFilter]);

  if (status === 'loading') return <LoadingState label="Loading drivers…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">All drivers</h2>
          <p className="text-xs text-text-muted">{filtered.length} of {drivers?.length ?? 0} drivers</p>
        </div>
        <div className="flex gap-2">
          <SearchInput value={query} onChange={setQuery} placeholder="Search by name, ID or license…" className="w-64" />
          <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
        </div>
      </div>

      <Card>
        <DriverTable drivers={filtered} />
      </Card>
    </div>
  );
}
