import { useState } from 'react';
import { Bell, Menu, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { BackendStatusBadge } from './BackendStatusBadge';
import { WebSocketStatusBadge } from './WebSocketStatusBadge';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getAlerts } from '@/services/api/incidentService';
import { useAuth } from '@/hooks/useAuth';
import { USE_MOCK_DATA } from '@/services/config';
import { isManagerRole } from '@/utils/roles';
import { Badge } from '@/components/ui/Badge';
import { severityTone } from '@/utils/statusColors';
import { timeAgo } from '@/utils/formatDate';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';

export function Topbar({ onMenuClick, title }: { onMenuClick: () => void; title: string }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const isManager = isManagerRole(user?.role);

  // Only fetch fleet-wide alerts for manager users
  const { data: alerts } = useAsyncData(
    () => (isManager ? getAlerts() : Promise.resolve([])),
    [isManager],
  );

  const unreadCount = alerts?.filter((a) => !a.read).length ?? 0;

  return (
    <header className="h-16 shrink-0 border-b border-border bg-surface flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="lg:hidden w-9 h-9 flex items-center justify-center rounded-md border border-border text-text-secondary"
          aria-label="Open navigation"
        >
          <Menu size={17} />
        </button>
        <h1 className="text-base font-semibold text-text-primary">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <BackendStatusBadge />
        <WebSocketStatusBadge />

        {/* Notifications — fleet managers only */}
        {isManager && (
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setNotifOpen((v) => !v);
                setUserOpen(false);
              }}
              aria-label="Notifications"
              className="relative w-9 h-9 flex items-center justify-center rounded-md border border-border text-text-secondary hover:bg-surface-inset transition-colors"
            >
              <Bell size={16} />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-status-danger-text text-white text-[10px] font-semibold flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-lg shadow-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <span className="text-sm font-semibold text-text-primary">Alerts</span>
                  <span className="text-xs text-text-muted">{unreadCount} unread</span>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {(alerts ?? []).slice(0, 6).map((alert) => (
                    <div key={alert.id} className="px-4 py-3 border-b border-border last:border-0 flex gap-3">
                      <Badge label="" dot tone={severityTone(alert.severity)} />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-text-primary leading-snug">{alert.message}</p>
                        <p className="text-[11px] text-text-muted mt-1">
                          {MONITORING_EVENT_LABELS[alert.type] ?? alert.type} · {timeAgo(alert.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setNotifOpen(false);
                    navigate('/incidents');
                  }}
                  className="w-full text-center text-xs font-medium text-brand-blue py-2.5 hover:bg-surface-inset"
                >
                  View all incidents
                </button>
              </div>
            )}
          </div>
        )}

        <ThemeToggle />

        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setUserOpen((v) => !v);
              setNotifOpen(false);
            }}
            className="flex items-center gap-2 pl-1 pr-2.5 py-1 rounded-md border border-border hover:bg-surface-inset transition-colors"
          >
            <span className="w-7 h-7 rounded-full bg-status-info-bg text-status-info-text flex items-center justify-center">
              <User size={14} />
            </span>
            <span className="text-sm font-medium text-text-primary hidden sm:inline">
              {user ? user.full_name : 'Guest'}
            </span>
          </button>
          {userOpen && (
            <div className="absolute right-0 mt-2 w-44 bg-surface border border-border rounded-lg shadow-lg overflow-hidden">
              <button
                type="button"
                onClick={() => {
                  setUserOpen(false);
                  navigate('/settings');
                }}
                className="w-full text-left px-4 py-2.5 text-sm text-text-primary hover:bg-surface-inset"
              >
                Settings
              </button>
              <button
                type="button"
                onClick={() => {
                  setUserOpen(false);
                  if (!USE_MOCK_DATA) logout();
                  navigate('/login');
                }}
                className="w-full text-left px-4 py-2.5 text-sm text-status-danger-text hover:bg-surface-inset"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
