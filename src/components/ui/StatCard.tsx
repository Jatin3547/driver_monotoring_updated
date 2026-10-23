import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trend?: { value: string; direction: 'up' | 'down'; positive: boolean };
  iconTone?: 'blue' | 'green' | 'amber' | 'red';
}

const toneClasses: Record<string, string> = {
  blue: 'bg-status-info-bg text-status-info-text',
  green: 'bg-status-success-bg text-status-success-text',
  amber: 'bg-status-warning-bg text-status-warning-text',
  red: 'bg-status-danger-bg text-status-danger-text',
};

export function StatCard({ label, value, icon: Icon, trend, iconTone = 'blue' }: StatCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wide">{label}</span>
        <span className={`w-8 h-8 rounded-md flex items-center justify-center ${toneClasses[iconTone]}`}>
          <Icon size={16} />
        </span>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-semibold text-text-primary">{value}</span>
        {trend && (
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-medium ${
              trend.positive ? 'text-status-success-text' : 'text-status-danger-text'
            }`}
          >
            {trend.direction === 'up' ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {trend.value}
          </span>
        )}
      </div>
    </div>
  );
}
