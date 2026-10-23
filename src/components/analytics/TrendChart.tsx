import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import { Card, CardHeader } from '@/components/ui/Card';
import type { IncidentBreakdownSlice } from '@/types';

const COLORS = ['#2563eb', '#dc2626', '#d97706', '#64748b', '#16a34a', '#7c3aed'];

export function TrendChart({ data }: { data: IncidentBreakdownSlice[] }) {
  return (
    <Card>
      <CardHeader title="Incidents by type" subtitle="Total over the last 30 days" />
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="type"
              width={100}
              tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
              cursor={{ fill: 'var(--color-surface-inset)' }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
              {data.map((entry, index) => (
                <Cell key={entry.type} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
