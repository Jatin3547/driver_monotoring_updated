import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Card, CardHeader } from '@/components/ui/Card';
import type { FleetSafetyTrendPoint } from '@/types';
import { formatDate } from '@/utils/formatDate';

export function SafetyScoreChart({ data }: { data: FleetSafetyTrendPoint[] }) {
  return (
    <Card>
      <CardHeader title="Safety score over time" subtitle="Fleet-wide average" />
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="safetyFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563eb" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(v: string) => formatDate(v).replace(/,.*/, '')}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              axisLine={{ stroke: 'var(--color-border)' }}
              tickLine={false}
            />
            <YAxis domain={[50, 100]} tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} width={32} />
            <Tooltip
              contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
              labelFormatter={(v) => formatDate(String(v))}
            />
            <Area type="monotone" dataKey="avgSafetyScore" name="Safety score" stroke="#2563eb" strokeWidth={2} fill="url(#safetyFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
