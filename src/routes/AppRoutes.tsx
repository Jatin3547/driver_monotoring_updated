import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { RequireAuth } from '@/routes/RequireAuth';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import DriversPage from '@/pages/DriversPage';
import DriverDetailPage from '@/pages/DriverDetailPage';
import VehiclesPage from '@/pages/VehiclesPage';
import VehicleDetailPage from '@/pages/VehicleDetailPage';
import MonitoringPage from '@/pages/MonitoringPage';
import GpsTrackingPage from '@/pages/GpsTrackingPage';
import IncidentsPage from '@/pages/IncidentsPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import SettingsPage from '@/pages/SettingsPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/drivers" element={<DriversPage />} />
        <Route path="/drivers/:id" element={<DriverDetailPage />} />
        <Route path="/vehicles" element={<VehiclesPage />} />
        <Route path="/vehicles/:id" element={<VehicleDetailPage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="/gps-tracking" element={<GpsTrackingPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
