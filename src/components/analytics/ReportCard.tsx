import { Card, CardHeader } from '@/components/ui/Card';
import type { DriverLeaderboardEntry } from '@/types';

export function ReportCard({ leaderboard }: { leaderboard: DriverLeaderboardEntry[] }) {
  const sorted = [...leaderboard].sort((a, b) => b.safetyScore - a.safetyScore);

  return (
    <Card>
      <CardHeader title="Driver safety leaderboard" subtitle="Ranked by safety score" />
      <ul className="space-y-1">
        {sorted.map((entry, index) => (
          <li key={entry.driverId} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
            <span className="w-5 text-xs font-medium text-text-muted text-center shrink-0">{index + 1}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">{entry.driverName}</p>
              <p className="text-xs text-text-muted">{entry.tripsCompleted} trips · {entry.incidentCount} incidents</p>
            </div>
            <span
              className={`text-sm font-semibold ${
                entry.safetyScore >= 80
                  ? 'text-status-success-text'
                  : entry.safetyScore >= 60
                    ? 'text-status-warning-text'
                    : 'text-status-danger-text'
              }`}
            >
              {entry.safetyScore}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
