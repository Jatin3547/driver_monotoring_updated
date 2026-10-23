import { useFleetSocketContext } from '@/hooks/useFleetSocketEvent';
import { USE_MOCK_DATA } from '@/services/config';

const LABELS: Record<string, string> = {
  connected: 'Live updates',
  connecting: 'Connecting…',
  reconnecting: 'Reconnecting…',
  disconnected: 'Offline',
};

const DOT_CLASS: Record<string, string> = {
  connected: 'bg-status-success-text',
  connecting: 'bg-status-warning-text animate-pulse',
  reconnecting: 'bg-status-warning-text animate-pulse',
  disconnected: 'bg-text-muted',
};

export function WebSocketStatusBadge() {
  const { status } = useFleetSocketContext();

  if (USE_MOCK_DATA) return null; // no socket in demo mode; BackendStatusBadge already covers this

  return (
    <span className="hidden md:inline-flex items-center gap-1.5 text-xs text-text-muted border border-border rounded-full px-2.5 py-1">
      <span className={`w-1.5 h-1.5 rounded-full ${DOT_CLASS[status]}`} />
      {LABELS[status]}
    </span>
  );
}
