// Central status→color mapping. Status color is the ONLY accent language in
// this UI (badges, chart lines, map markers) — keep every domain funneled
// through here so the palette stays consistent.

export type StatusTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info';

const toneClasses: Record<StatusTone, string> = {
  success: 'bg-status-success-bg text-status-success-text border-status-success-border',
  warning: 'bg-status-warning-bg text-status-warning-text border-status-warning-border',
  danger: 'bg-status-danger-bg text-status-danger-text border-status-danger-border',
  neutral: 'bg-status-neutral-bg text-status-neutral-text border-status-neutral-border',
  info: 'bg-status-info-bg text-status-info-text border-status-info-border',
};

const toneHex: Record<StatusTone, string> = {
  success: '#16A34A',
  warning: '#D97706',
  danger: '#DC2626',
  neutral: '#64748B',
  info: '#2563EB',
};

export function toneClass(tone: StatusTone): string {
  return toneClasses[tone];
}

export function toneHexColor(tone: StatusTone): string {
  return toneHex[tone];
}

export function driverStatusTone(status: string): StatusTone {
  switch (status) {
    case 'active':
    case 'on-trip':
      return 'success';
    case 'off-duty':
      return 'neutral';
    case 'suspended':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function vehicleStatusTone(status: string): StatusTone {
  switch (status) {
    case 'active':
      return 'success';
    case 'idle':
      return 'info';
    case 'maintenance':
      return 'warning';
    case 'offline':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function severityTone(severity: string): StatusTone {
  switch (severity) {
    case 'high':
      return 'danger';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    default:
      return 'neutral';
  }
}

export function incidentStatusTone(status: string): StatusTone {
  switch (status) {
    case 'open':
      return 'danger';
    case 'reviewed':
      return 'warning';
    case 'resolved':
      return 'success';
    default:
      return 'neutral';
  }
}

export function monitoringSignalTone(status: string): StatusTone {
  switch (status) {
    case 'normal':
      return 'success';
    case 'warning':
      return 'warning';
    case 'critical':
      return 'danger';
    case 'no-signal':
      return 'neutral';
    default:
      return 'neutral';
  }
}
