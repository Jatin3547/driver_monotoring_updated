import { useMemo, useState } from 'react';
import { useIncidents } from '@/hooks/useIncidents';
import { useDrivers } from '@/hooks/useDrivers';
import { useVehicles } from '@/hooks/useVehicles';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { IncidentTable } from '@/components/incidents/IncidentTable';
import { IncidentDetailPanel } from '@/components/incidents/IncidentDetailPanel';
import { Card } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { SearchInput } from '@/components/ui/SearchInput';
import { Select } from '@/components/ui/Select';
import { LoadingState, ErrorState } from '@/components/ui/States';
import type { Incident } from '@/types';

const SEVERITY_OPTIONS = [
  { value: 'all', label: 'All severities' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'resolved', label: 'Resolved' },
];

export default function IncidentsPage() {
  const { data: incidents, status, error, refetch } = useIncidents();
  const { data: drivers } = useDrivers();
  const { data: vehicles } = useVehicles();

  const [query, setQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState<Incident | null>(null);

  // New incidents from the AI escalation pipeline appear here live.
  useFleetSocketEvent('incident_created', () => {
    refetch();
  });

  const driverById = useMemo(() => new Map((drivers ?? []).map((d) => [d.id, d])), [drivers]);
  const vehicleById = useMemo(() => new Map((vehicles ?? []).map((v) => [v.id, v])), [vehicles]);

  const filtered = useMemo(() => {
    if (!incidents) return [];
    return incidents.filter((i) => {
      const driverName = driverById.get(i.driverId)?.name ?? '';
      const matchesQuery =
        query.trim() === '' ||
        driverName.toLowerCase().includes(query.toLowerCase()) ||
        i.type.toLowerCase().includes(query.toLowerCase()) ||
        i.location.toLowerCase().includes(query.toLowerCase());
      const matchesSeverity = severityFilter === 'all' || i.severity === severityFilter;
      const matchesStatus = statusFilter === 'all' || i.status === statusFilter;
      return matchesQuery && matchesSeverity && matchesStatus;
    });
  }, [incidents, query, severityFilter, statusFilter, driverById]);

  if (status === 'loading') return <LoadingState label="Loading incidents…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">All incidents</h2>
          <p className="text-xs text-text-muted">{filtered.length} of {incidents?.length ?? 0} incidents</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <SearchInput value={query} onChange={setQuery} placeholder="Search by driver, type or location…" className="w-64" />
          <Select value={severityFilter} onChange={setSeverityFilter} options={SEVERITY_OPTIONS} />
          <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
        </div>
      </div>

      <Card>
        <IncidentTable
          incidents={filtered}
          drivers={drivers ?? []}
          vehicles={vehicles ?? []}
          onSelect={(incident) => setSelected(incident)}
        />
      </Card>

      <Modal open={selected !== null} onClose={() => setSelected(null)} title="Incident details">
        {selected && (
          <IncidentDetailPanel
            incident={selected}
            driver={driverById.get(selected.driverId)}
            vehicle={selected.vehicleId ? vehicleById.get(selected.vehicleId) : undefined}
            onStatusUpdated={() => refetch()}
          />
        )}
      </Modal>
    </div>
  );
}
