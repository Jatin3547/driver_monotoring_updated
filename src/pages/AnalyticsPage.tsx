import { useAsyncData } from '@/hooks/useAsyncData';
import {
  getSafetyTrend,
  getIncidentBreakdown,
  getDriverLeaderboard,
  getFleetUtilization,
} from '@/services/api/analyticsService';
import { SafetyScoreChart } from '@/components/analytics/SafetyScoreChart';
import { TrendChart } from '@/components/analytics/TrendChart';
import { ReportCard } from '@/components/analytics/ReportCard';
import { Card, CardHeader } from '@/components/ui/Card';
import { LoadingState, ErrorState } from '@/components/ui/States';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { formatDate } from '@/utils/formatDate';

export default function AnalyticsPage() {
  const { data: trend, status, error, refetch } = useAsyncData(() => getSafetyTrend(), []);
  const { data: breakdown } = useAsyncData(() => getIncidentBreakdown(), []);
  const { data: leaderboard } = useAsyncData(() => getDriverLeaderboard(), []);
  const { data: utilization } = useAsyncData(() => getFleetUtilization(), []);

  if (status === 'loading') return <LoadingState label="Crunching fleet analytics…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <SafetyScoreChart data={trend ?? []} />
        </div>
        <ReportCard leaderboard={leaderboard ?? []} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <TrendChart data={breakdown ?? []} />

        <Card>
          <CardHeader title="Fleet utilization" subtitle="Vehicle status mix over the last 7 days" />
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={utilization ?? []} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(v: string) => formatDate(v).replace(/,.*/, '')}
                  tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                  axisLine={{ stroke: 'var(--color-border)' }}
                  tickLine={false}
                />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} width={28} />
                <Tooltip
                  contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(v) => formatDate(String(v))}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="activeVehicles" name="Active" stackId="a" fill="#16a34a" radius={[0, 0, 0, 0]} />
                <Bar dataKey="idleVehicles" name="Idle" stackId="a" fill="#2563eb" radius={[0, 0, 0, 0]} />
                <Bar dataKey="maintenanceVehicles" name="Maintenance" stackId="a" fill="#d97706" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
