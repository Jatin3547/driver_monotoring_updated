import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

const TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/driver': 'My Dashboard',
  '/drivers': 'Drivers',
  '/vehicles': 'Vehicles',
  '/monitoring': 'Live AI Monitoring',
  '/gps-tracking': 'GPS Tracking',
  '/incidents': 'Incidents',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

function resolveTitle(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith('/drivers/')) return 'Driver Details';
  if (pathname.startsWith('/vehicles/')) return 'Vehicle Details';
  return 'FleetGuard';
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-surface-muted">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onMenuClick={() => setSidebarOpen((v) => !v)} title={resolveTitle(location.pathname)} />
        <main className="flex-1 p-4 lg:p-6 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
