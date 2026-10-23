import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Truck,
  ScanEye,
  MapPin,
  AlertTriangle,
  BarChart3,
  Settings,
  ShieldCheck,
} from 'lucide-react';
import { APP_NAME } from '@/utils/constants';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/drivers', label: 'Drivers', icon: Users },
  { to: '/vehicles', label: 'Vehicles', icon: Truck },
  { to: '/monitoring', label: 'Live Monitoring', icon: ScanEye },
  { to: '/gps-tracking', label: 'GPS Tracking', icon: MapPin },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate?: () => void }) {
  return (
    <aside
      className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-brand-navy text-slate-100 flex flex-col transition-transform duration-200 ${
        open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}
    >
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-white/10 shrink-0">
        <span className="w-8 h-8 rounded-md bg-brand-blue flex items-center justify-center">
          <ShieldCheck size={17} className="text-white" />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-white">{APP_NAME}</p>
          <p className="text-[11px] text-slate-400">Fleet &amp; Driver Safety</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-blue text-white'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            <item.icon size={17} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-white/10 text-[11px] text-slate-500">
        Phase 1 — Frontend preview
        <br />
        Backend connection pending
      </div>
    </aside>
  );
}
