import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Card, CardHeader } from '@/components/ui/Card';
import type { FleetSafetyTrendPoint } from '@/types';
import { formatDate } from '@/utils/formatDate';

export function FleetActivityChart({ data }: { data: FleetSafetyTrendPoint[] }) {
  return (
    <Card>
      <CardHeader title="Fleet safety trend" subtitle="Average safety score, last 25 days" />
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(v: string) => formatDate(v).replace(/,.*/, '')}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              axisLine={{ stroke: 'var(--color-border)' }}
              tickLine={false}
            />
            <YAxis
              domain={[50, 100]}
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                fontSize: 12,
              }}
              labelFormatter={(v) => formatDate(String(v))}
            />
            <Line
              type="monotone"
              dataKey="avgSafetyScore"
              name="Avg. safety score"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
