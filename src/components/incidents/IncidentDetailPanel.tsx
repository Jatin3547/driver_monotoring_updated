import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { severityTone, incidentStatusTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatDate';
import { updateIncidentStatus } from '@/services/api/incidentService';
import { MapPin, User, Truck, Clock, CheckCircle2, ShieldCheck, Video } from 'lucide-react';
import type { Driver, Incident, Vehicle } from '@/types';

interface Props {
  incident: Incident;
  driver?: Driver;
  vehicle?: Vehicle;
  onStatusUpdated?: (updated: Incident) => void;
}

export function IncidentDetailPanel({ incident, driver, vehicle, onStatusUpdated }: Props) {
  const [currentStatus, setCurrentStatus] = useState<string>(incident.status);
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleUpdate = async (newStatus: 'reviewed' | 'resolved') => {
    setUpdating(true);
    setMessage(null);
    try {
      const updated = await updateIncidentStatus(incident.id, newStatus, 'Fleet Admin');
      setCurrentStatus(newStatus);
      setMessage(`Incident marked as ${newStatus}.`);
      if (onStatusUpdated) onStatusUpdated(updated);
    } catch {
      setMessage('Failed to update incident status.');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge label={incident.severity} tone={severityTone(incident.severity)} />
          <Badge label={currentStatus} tone={incidentStatusTone(currentStatus)} />
        </div>
        <span className="text-xs text-text-muted font-mono">{incident.id}</span>
      </div>

      <div className="aspect-video bg-surface-inset rounded-md flex flex-col items-center justify-center text-text-muted p-4 relative overflow-hidden border border-border">
        {incident.snapshotUrl ? (
          <img
            src={incident.snapshotUrl}
            alt="Event Evidence Frame"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-center">
            <Video size={30} className="mx-auto mb-2 text-text-muted" />
            <p className="text-xs font-medium text-text-primary">Protected Video Evidence Metadata</p>
            <p className="text-[11px] text-text-muted mt-0.5">
              Pre-event (5s) & post-event (3s) clip buffer attached to ID #{incident.id}
            </p>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-text-primary">
          {MONITORING_EVENT_LABELS[incident.type] ?? incident.type}
        </h3>
        <p className="text-sm text-text-secondary mt-1">{incident.description}</p>
      </div>

      <dl className="grid grid-cols-1 gap-2.5 text-sm pt-3 border-t border-border">
        <div className="flex items-center gap-2 text-text-secondary">
          <User size={14} className="text-text-muted" /> {driver?.name ?? incident.driverId}
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Truck size={14} className="text-text-muted" /> {vehicle?.plateNumber ?? incident.vehicleId ?? 'Unassigned'}
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <MapPin size={14} className="text-text-muted" /> {incident.location}
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Clock size={14} className="text-text-muted" /> {formatDateTime(incident.timestamp)}
        </div>
        {incident.tripId && (
          <div className="flex items-center gap-2 text-text-secondary">
            <ShieldCheck size={14} className="text-text-muted" /> Trip ID: {incident.tripId}
          </div>
        )}
      </dl>

      {/* Incident Review & Resolution Actions */}
      <div className="pt-3 border-t border-border flex items-center justify-between">
        {message ? (
          <span className="text-xs text-status-success-text font-medium">{message}</span>
        ) : (
          <span className="text-xs text-text-muted">Operator Resolution Actions:</span>
        )}

        <div className="flex items-center gap-2">
          {currentStatus === 'open' && (
            <Button
              variant="secondary"
              size="sm"
              disabled={updating}
              onClick={() => handleUpdate('reviewed')}
            >
              Mark Reviewed
            </Button>
          )}

          {currentStatus !== 'resolved' ? (
            <Button
              size="sm"
              disabled={updating}
              onClick={() => handleUpdate('resolved')}
            >
              <CheckCircle2 size={13} className="mr-1" />
              Resolve Incident
            </Button>
          ) : (
            <Badge label="Resolved" tone="success" dot />
          )}
        </div>
      </div>
    </div>
  );
}
