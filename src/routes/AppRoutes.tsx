import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { RequireAuth } from '@/routes/RequireAuth';
import { RequireRole } from '@/routes/RequireRole';
import { LoadingState } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';
import { homePathForRole } from '@/utils/roles';

const LoginPage = lazy(() => import('@/pages/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const DriverDashboardPage = lazy(() => import('@/pages/DriverDashboardPage'));
const DriversPage = lazy(() => import('@/pages/DriversPage'));
const DriverDetailPage = lazy(() => import('@/pages/DriverDetailPage'));
const VehiclesPage = lazy(() => import('@/pages/VehiclesPage'));
const VehicleDetailPage = lazy(() => import('@/pages/VehicleDetailPage'));
const MonitoringPage = lazy(() => import('@/pages/MonitoringPage'));
const GpsTrackingPage = lazy(() => import('@/pages/GpsTrackingPage'));
const IncidentsPage = lazy(() => import('@/pages/IncidentsPage'));
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));

/** Smart redirect from "/" for authenticated users based on role. */
function RootRedirect() {
  const { user } = useAuth();
  if (user?.role === 'driver') {
    return <Navigate to="/driver" replace />;
  }
  return <DashboardPage />;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingState label="Loading page…" />}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Shared layout (auth required for all) */}
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        {/* Root: smart redirect — drivers go to /driver, managers stay on / */}
        <Route path="/" element={<RootRedirect />} />

        {/* ── Driver-only routes ─────────────────────────────────── */}
        <Route
          path="/driver"
          element={
            <RequireRole allow="driver">
              <DriverDashboardPage />
            </RequireRole>
          }
        />

        {/* ── Manager-only routes ─────────────────────────────────── */}
        <Route
          path="/drivers"
          element={
            <RequireRole allow="manager">
              <DriversPage />
            </RequireRole>
          }
        />
        <Route
          path="/drivers/:id"
          element={
            <RequireRole allow="manager">
              <DriverDetailPage />
            </RequireRole>
          }
        />
        <Route
          path="/vehicles"
          element={
            <RequireRole allow="manager">
              <VehiclesPage />
            </RequireRole>
          }
        />
        <Route
          path="/vehicles/:id"
          element={
            <RequireRole allow="manager">
              <VehicleDetailPage />
            </RequireRole>
          }
        />
        <Route
          path="/monitoring"
          element={
            <RequireRole allow="manager">
              <MonitoringPage />
            </RequireRole>
          }
        />
        <Route
          path="/gps-tracking"
          element={
            <RequireRole allow="manager">
              <GpsTrackingPage />
            </RequireRole>
          }
        />
        <Route
          path="/incidents"
          element={
            <RequireRole allow="manager">
              <IncidentsPage />
            </RequireRole>
          }
        />
        <Route
          path="/analytics"
          element={
            <RequireRole allow="manager">
              <AnalyticsPage />
            </RequireRole>
          }
        />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Catch-all: redirect to role home */}
        <Route path="*" element={<RoleHomeRedirect />} />
      </Route>
    </Routes>
    </Suspense>
  );
}

function RoleHomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={homePathForRole(user?.role)} replace />;
}
