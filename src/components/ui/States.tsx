import type { LucideIcon } from 'lucide-react';
import { Inbox, Loader2 } from 'lucide-react';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
      <Loader2 size={22} className="animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-status-danger-text">
      <span className="text-sm font-medium">Couldn't load this data</span>
      <span className="text-xs text-text-muted">{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-xs font-medium text-brand-blue hover:underline"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center border border-dashed border-border rounded-lg">
      <Icon size={22} className="text-text-muted" />
      <span className="text-sm font-medium text-text-primary">{title}</span>
      {description && <span className="text-xs text-text-muted max-w-xs">{description}</span>}
    </div>
  );
}
