import type { StatusTone } from '@/utils/statusColors';
import { toneClass } from '@/utils/statusColors';

interface BadgeProps {
  label: string;
  tone: StatusTone;
  dot?: boolean;
}

export function Badge({ label, tone, dot = true }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap ${toneClass(tone)}`}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />}
      {label}
    </span>
  );
}
