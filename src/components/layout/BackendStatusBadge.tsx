import { useEffect, useState } from 'react';
import { checkBackendHealth } from '@/services/api/healthService';
import { USE_MOCK_DATA } from '@/services/config';

const POLL_INTERVAL_MS = 15000;

export function BackendStatusBadge() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      const ok = await checkBackendHealth();
      if (!cancelled) setConnected(ok);
    }
    check();
    const interval = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // In mock mode the backend is optional, so we show a neutral label
  // rather than implying something is broken.
  if (USE_MOCK_DATA) {
    return (
      <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-text-muted border border-border rounded-full px-2.5 py-1">
        <span className="w-1.5 h-1.5 rounded-full bg-text-muted" />
        Demo data
      </span>
    );
  }

  if (connected === null) {
    return (
      <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-text-muted border border-border rounded-full px-2.5 py-1">
        <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" />
        Checking backend…
      </span>
    );
  }

  return connected ? (
    <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-status-success-text border border-status-success-border bg-status-success-bg rounded-full px-2.5 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-status-success-text" />
      Backend Connected
    </span>
  ) : (
    <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-status-danger-text border border-status-danger-border bg-status-danger-bg rounded-full px-2.5 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-status-danger-text" />
      Backend Offline
    </span>
  );
}
