import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { severityTone, incidentStatusTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatDate';
import { updateIncidentStatus, deleteIncident } from '@/services/api/incidentService';
import {
  getEvidenceByIncident,
  verifyEvidenceHash,
  toggleEvidenceProtection,
} from '@/services/api/evidenceService';
import { API_BASE_URL } from '@/services/config';
import { getStoredToken } from '@/services/api/authService';
import {
  MapPin,
  User,
  Truck,
  Clock,
  CheckCircle2,
  ShieldCheck,
  Video,
  Download,
  ShieldAlert,
  Lock,
  Unlock,
  Check,
  AlertCircle,
  Camera,
  Play,
  RotateCcw,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import type { Driver, Evidence, Incident, Vehicle } from '@/types';

interface Props {
  incident: Incident;
  driver?: Driver;
  vehicle?: Vehicle;
  onStatusUpdated?: (updated: Incident) => void;
  onDeleted?: (incidentId: string) => void;
}

export function IncidentDetailPanel({ incident, driver, vehicle, onStatusUpdated, onDeleted }: Props) {
  const [currentStatus, setCurrentStatus] = useState<string>(incident.status);
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteIncident(incident.id);
      setShowDeleteConfirm(false);
      if (onDeleted) {
        onDeleted(incident.id);
      }
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to delete incident.');
      setDeleting(false);
    }
  };

  // Phase 3 Evidence state
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [activeMediaTab, setActiveMediaTab] = useState<'video' | 'snapshot'>('video');
  const [verifyingHash, setVerifyingHash] = useState(false);
  const [hashResult, setHashResult] = useState<{ matches: boolean; message: string } | null>(null);
  const [isProtected, setIsProtected] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchEvidence = async () => {
      setEvidenceLoading(true);
      setHashResult(null);
      try {
        const ev = await getEvidenceByIncident(incident.id);
        if (active) {
          setEvidence(ev);
          setIsProtected(ev?.isProtected ?? false);
          if (ev?.status === 'available') {
            setActiveMediaTab('video');
          } else if (incident.snapshotUrl) {
            setActiveMediaTab('snapshot');
          }
        }
      } catch {
        if (active) setEvidence(null);
      } finally {
        if (active) setEvidenceLoading(false);
      }
    };

    fetchEvidence();
    return () => {
      active = false;
    };
  }, [incident.id, incident.snapshotUrl]);

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

  const handleVerifyHash = async () => {
    if (!evidence) return;
    setVerifyingHash(true);
    setHashResult(null);
    try {
      const result = await verifyEvidenceHash(evidence.id);
      setHashResult({
        matches: result.matches,
        message: result.details,
      });
    } catch {
      setHashResult({
        matches: false,
        message: 'Failed to verify file hash with server',
      });
    } finally {
      setVerifyingHash(false);
    }
  };

  const handleToggleProtect = async () => {
    if (!evidence) return;
    try {
      const next = !isProtected;
      const updated = await toggleEvidenceProtection(evidence.id, next);
      setIsProtected(updated.isProtected);
      setEvidence(updated);
    } catch {
      // Toggle failure
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const evidenceToken = getStoredToken();
  const evidenceAuth = evidenceToken ? `?token=${encodeURIComponent(evidenceToken)}` : '';
  const videoStreamUrl = evidence?.id
    ? `${API_BASE_URL}/evidence/${evidence.id}/stream${evidenceAuth}`
    : undefined;

  const snapshotUrl = evidence?.id
    ? `${API_BASE_URL}/evidence/${evidence.id}/snapshot${evidenceAuth}`
    : incident.snapshotUrl;

  const downloadVideoUrl = evidence?.id
    ? `${API_BASE_URL}/evidence/${evidence.id}/download${evidenceAuth}`
    : undefined;

  return (
    <div className="space-y-4">
      {/* Header status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge label={incident.severity} tone={severityTone(incident.severity)} />
          <Badge label={currentStatus} tone={incidentStatusTone(currentStatus)} />
          {evidence && (
            <Badge
              label={`Evidence: ${evidence.status.toUpperCase()}`}
              tone={
                evidence.status === 'available'
                  ? 'success'
                  : evidence.status === 'pending'
                  ? 'warning'
                  : evidence.status === 'failed'
                  ? 'danger'
                  : 'neutral'
              }
              dot={evidence.status === 'pending'}
            />
          )}
        </div>
        <span className="text-xs text-text-muted font-mono">{incident.id}</span>
      </div>

      {/* Media Player / Snapshot Preview Section */}
      <div className="border border-border rounded-lg overflow-hidden bg-black/90">
        {/* Tab switch bar */}
        <div className="bg-surface-inset px-3 py-1.5 flex items-center justify-between border-b border-border text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveMediaTab('video')}
              className={`px-2.5 py-1 rounded font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                activeMediaTab === 'video'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <Video size={13} /> Video Clip (MP4)
            </button>
            <button
              type="button"
              onClick={() => setActiveMediaTab('snapshot')}
              className={`px-2.5 py-1 rounded font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                activeMediaTab === 'snapshot'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <Camera size={13} /> Still Snapshot
            </button>
          </div>

          {evidence?.durationSeconds && (
            <span className="text-[11px] text-text-muted font-mono">
              Duration: {evidence.durationSeconds.toFixed(1)}s (5s pre + 10s post)
            </span>
          )}
        </div>

        {/* Media Frame Viewport */}
        <div className="aspect-video relative flex items-center justify-center bg-black">
          {activeMediaTab === 'video' ? (
            evidence?.status === 'available' && videoStreamUrl ? (
              <video
                key={videoStreamUrl}
                controls
                playsInline
                preload="metadata"
                src={videoStreamUrl}
                className="w-full h-full object-contain"
              >
                Your browser does not support HTML5 video streaming.
              </video>
            ) : evidence?.status === 'pending' ? (
              <div className="text-center p-6 text-yellow-400">
                <Play size={32} className="mx-auto mb-2 animate-spin" />
                <p className="text-sm font-semibold">Transcoding Video Evidence...</p>
                <p className="text-xs text-text-muted mt-1">
                  Converting WebM buffer (5s pre-event + 10s post-event) to web-optimized MP4
                </p>
              </div>
            ) : evidence?.status === 'failed' ? (
              <div className="text-center p-6 text-red-400">
                <ShieldAlert size={32} className="mx-auto mb-2" />
                <p className="text-sm font-semibold">Evidence Capture Unavailable</p>
                <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                  {evidence.errorMessage || 'Evidence file could not be created or storage quota was exceeded.'}
                </p>
              </div>
            ) : evidence?.status === 'expired' ? (
              <div className="text-center p-6 text-text-muted">
                <Clock size={32} className="mx-auto mb-2" />
                <p className="text-sm font-semibold text-text-primary">Evidence Expired</p>
                <p className="text-xs mt-1">
                  This recording was purged under the automated 7-day retention policy.
                </p>
              </div>
            ) : (
              <div className="text-center p-6 text-text-muted">
                <Video size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm font-semibold text-text-primary">No Recorded Clip Attached</p>
                <p className="text-xs mt-1">
                  Video evidence is captured for critical events during active webcam monitoring.
                </p>
              </div>
            )
          ) : (
            /* Snapshot tab */
            snapshotUrl ? (
              <img
                src={snapshotUrl}
                alt="Event Evidence Still Snapshot"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-6 text-text-muted">
                <Camera size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm font-medium text-text-primary">No Snapshot Available</p>
              </div>
            )
          )}
        </div>
      </div>

      {/* Phase 3 Evidence Metadata & Integrity Card */}
      {evidence && evidence.status === 'available' && (
        <div className="bg-surface-inset border border-border rounded-lg p-3 space-y-2.5 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <span className="font-semibold text-text-primary flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-status-success-text" />
              Verified Evidence Package
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleToggleProtect}
                className={`px-2 py-1 rounded border text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer ${
                  isProtected
                    ? 'bg-status-warning-bg border-status-warning-border text-status-warning-text'
                    : 'bg-surface border-border text-text-muted hover:text-text-primary'
                }`}
                title={isProtected ? 'Protected from 7-day retention cleanup' : 'Click to protect from 7-day retention'}
              >
                {isProtected ? <Lock size={11} /> : <Unlock size={11} />}
                {isProtected ? 'Retention Protected' : 'Protect Retention'}
              </button>

              {downloadVideoUrl && (
                <a
                  href={downloadVideoUrl}
                  download
                  className="px-2 py-1 rounded bg-surface border border-border hover:bg-surface text-text-primary font-medium flex items-center gap-1 transition-colors"
                >
                  <Download size={11} /> Download MP4
                </a>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-text-secondary text-[11px]">
            <div>
              <span className="text-text-muted block">Format:</span>
              <span className="font-mono text-text-primary uppercase">{evidence.fileType.split('/')[1] || 'MP4'} (H.264)</span>
            </div>
            <div>
              <span className="text-text-muted block">File Size:</span>
              <span className="font-mono text-text-primary">{formatBytes(evidence.fileSizeBytes)}</span>
            </div>
            <div>
              <span className="text-text-muted block">Timeline:</span>
              <span className="text-text-primary">5s Pre + 10s Post</span>
            </div>
            <div>
              <span className="text-text-muted block">Cloud Status:</span>
              <span className="text-text-primary font-medium capitalize">{evidence.cloudUploadStatus}</span>
            </div>
          </div>

          {/* Cryptographic SHA-256 Digest & Verification */}
          {evidence.sha256Hash && (
            <div className="pt-2 border-t border-border/80 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-text-muted font-medium">SHA-256 Hash Digest:</span>
                <button
                  type="button"
                  onClick={handleVerifyHash}
                  disabled={verifyingHash}
                  className="text-primary hover:text-primary/80 font-medium flex items-center gap-1 cursor-pointer disabled:opacity-50"
                >
                  {verifyingHash ? <RotateCcw size={11} className="animate-spin" /> : <Check size={11} />}
                  Verify Hash on Disk
                </button>
              </div>
              <p className="font-mono text-[10px] bg-surface p-1.5 rounded border border-border text-text-secondary break-all">
                {evidence.sha256Hash}
              </p>
              {hashResult && (
                <p
                  className={`text-[11px] font-medium flex items-center gap-1 ${
                    hashResult.matches ? 'text-status-success-text' : 'text-status-danger-text'
                  }`}
                >
                  {hashResult.matches ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                  {hashResult.message}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Incident Details & Metadata */}
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

      {/* Incident Review, Resolution & Deletion Actions */}
      <div className="pt-3 border-t border-border space-y-3">
        <div className="flex items-center justify-between">
          {message ? (
            <span className="text-xs text-status-success-text font-medium">{message}</span>
          ) : (
            <span className="text-xs text-text-muted">Operator Actions:</span>
          )}

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={updating || deleting}
              onClick={() => setShowDeleteConfirm(!showDeleteConfirm)}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/20"
              title="Permanently remove incident and purge associated video files"
            >
              <Trash2 size={13} className="mr-1" />
              Delete Incident
            </Button>

            {currentStatus === 'open' && (
              <Button
                variant="secondary"
                size="sm"
                disabled={updating || deleting}
                onClick={() => handleUpdate('reviewed')}
              >
                Mark Reviewed
              </Button>
            )}

            {currentStatus !== 'resolved' ? (
              <Button
                size="sm"
                disabled={updating || deleting}
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

        {/* Delete Confirmation Modal / Banner */}
        {showDeleteConfirm && (
          <div className="p-3 rounded-lg border border-red-500/30 bg-red-950/20 text-text-primary space-y-2 animate-in fade-in">
            <div className="flex items-start gap-2">
              <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-red-400">Permanently Delete Incident & Evidence?</p>
                <p className="text-xs text-text-muted">
                  This will permanently delete incident <code className="text-text-primary font-mono">{incident.id.slice(0, 8)}</code>,
                  purge its recorded MP4 video and snapshot files from disk, and adjust the driver's safety incident count. This cannot be undone.
                </p>
              </div>
            </div>

            {deleteError && (
              <p className="text-xs text-red-400 font-medium pl-6">{deleteError}</p>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <Button
                variant="secondary"
                size="sm"
                disabled={deleting}
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={deleting}
                onClick={handleDelete}
                className="bg-red-600 hover:bg-red-700 text-white border-transparent"
              >
                <Trash2 size={13} className="mr-1" />
                {deleting ? 'Deleting...' : 'Confirm Delete'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
