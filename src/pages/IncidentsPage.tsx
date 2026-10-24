import { useMemo, useState, useEffect } from 'react';
import { useIncidents } from '@/hooks/useIncidents';
import { useDrivers } from '@/hooks/useDrivers';
import { useVehicles } from '@/hooks/useVehicles';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { IncidentTable } from '@/components/incidents/IncidentTable';
import { IncidentDetailPanel } from '@/components/incidents/IncidentDetailPanel';
import { Card } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { SearchInput } from '@/components/ui/SearchInput';
import { Select } from '@/components/ui/Select';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { Video, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
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

const PAGE_SIZE = 15;

export default function IncidentsPage() {
  const { data: incidents, status, error, refetch } = useIncidents();
  const { data: drivers } = useDrivers();
  const { data: vehicles } = useVehicles();

  const [query, setQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [onlyWithVideo, setOnlyWithVideo] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [page, setPage] = useState(1);

  // Live WebSocket updates: new incidents, deletions, or newly uploaded video evidence
  useFleetSocketEvent('incident_created', () => {
    refetch();
  });
  useFleetSocketEvent('incident_deleted', () => {
    refetch();
  });
  useFleetSocketEvent('evidence_uploaded', () => {
    refetch();
  });

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [query, severityFilter, statusFilter, onlyWithVideo]);

  const driverById = useMemo(() => new Map((drivers ?? []).map((d) => [d.id, d])), [drivers]);
  const vehicleById = useMemo(() => new Map((vehicles ?? []).map((v) => [v.id, v])), [vehicles]);

  const filtered = useMemo(() => {
    if (!incidents) return [];
    return incidents.filter((i) => {
      if (onlyWithVideo && !i.evidenceId) return false;

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
  }, [incidents, query, severityFilter, statusFilter, onlyWithVideo, driverById]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  if (status === 'loading') return <LoadingState label="Loading incidents…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  const hasAnyIncidents = (incidents?.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">All incidents</h2>
          <p className="text-xs text-text-muted">
            {hasAnyIncidents ? `${filtered.length} of ${incidents?.length ?? 0} incidents` : 'Clean safety history'}
          </p>
        </div>
        {hasAnyIncidents && (
          <div className="flex gap-2 flex-wrap items-center">
            <SearchInput
              value={query}
              onChange={setQuery}
              placeholder="Search by driver, type or location…"
              className="w-56"
            />
            <Select value={severityFilter} onChange={setSeverityFilter} options={SEVERITY_OPTIONS} />
            <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
            <button
              type="button"
              onClick={() => setOnlyWithVideo(!onlyWithVideo)}
              className={`text-xs px-2.5 py-1.5 rounded border font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                onlyWithVideo
                  ? 'bg-primary text-white border-primary shadow-xs'
                  : 'bg-surface border-border text-text-muted hover:text-text-primary'
              }`}
              title="Filter to incidents with recorded video evidence"
            >
              <Video size={13} /> Has Video Evidence
            </button>
          </div>
        )}
      </div>

      {!hasAnyIncidents ? (
        /* Empty State: Pristine Safety Record */
        <Card className="p-12 text-center flex flex-col items-center justify-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck size={28} />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-text-primary">Clean Safety Record</h3>
            <p className="text-sm text-text-muted max-w-md mx-auto">
              No safety incidents are currently recorded. The system is actively monitoring driving behavior; qualifying critical events (e.g. eye closure, drowsiness, mobile phone usage) will automatically capture genuine MP4 video evidence and appear here.
            </p>
          </div>
        </Card>
      ) : filtered.length === 0 ? (
        /* Filtered Empty State */
        <Card className="p-8 text-center text-text-muted text-sm">
          No incidents match the active search or filter criteria.
        </Card>
      ) : (
        /* Incident Table with Pagination */
        <Card className="overflow-hidden">
          <IncidentTable
            incidents={paginated}
            drivers={drivers ?? []}
            vehicles={vehicles ?? []}
            onSelect={(incident) => setSelected(incident)}
          />
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-text-muted">
              <span>
                Showing {(page - 1) * PAGE_SIZE + 1} to {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} incidents
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={14} /> Previous
                </Button>
                <span className="px-2 font-medium text-text-primary">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      <Modal open={selected !== null} onClose={() => setSelected(null)} title="Incident details">
        {selected && (
          <IncidentDetailPanel
            incident={selected}
            driver={driverById.get(selected.driverId)}
            vehicle={selected.vehicleId ? vehicleById.get(selected.vehicleId) : undefined}
            onStatusUpdated={() => refetch()}
            onDeleted={() => {
              setSelected(null);
              refetch();
            }}
          />
        )}
      </Modal>
    </div>
  );
}
