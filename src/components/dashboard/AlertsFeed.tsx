import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { severityTone } from '@/utils/statusColors';
import { timeAgo } from '@/utils/formatDate';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import type { Alert } from '@/types';
import { BellOff } from 'lucide-react';

export function AlertsFeed({ alerts }: { alerts: Alert[] }) {
  const sorted = [...alerts].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );

  return (
    <Card>
      <CardHeader title="Live alerts feed" subtitle="Most recent safety and fleet events" />
      {sorted.length === 0 ? (
        <EmptyState icon={BellOff} title="No alerts" description="Everything is running normally." />
      ) : (
        <ul className="space-y-3 max-h-96 overflow-y-auto">
          {sorted.map((alert) => (
            <li key={alert.id} className="flex gap-3 items-start">
              <Badge label={alert.severity} tone={severityTone(alert.severity)} />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-text-primary leading-snug">{alert.message}</p>
                <p className="text-xs text-text-muted mt-0.5">
                  {MONITORING_EVENT_LABELS[alert.type] ?? alert.type} · {timeAgo(alert.timestamp)}
                </p>
              </div>
              {!alert.read && <span className="w-2 h-2 rounded-full bg-brand-blue mt-1.5 shrink-0" aria-label="Unread" />}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
