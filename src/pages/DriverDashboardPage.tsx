import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Gauge, MapPin, Route, ShieldCheck, Timer, Wifi } from 'lucide-react';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getMyDriverProfile } from '@/services/api/driverService';
import { getMyTrips } from '@/services/api/tripService';
import { getMyIncidents } from '@/services/api/incidentService';
import { getAssignedVehicle } from '@/services/api/vehicleService';
import { getMyVehicleLocation } from '@/services/api/gpsService';
import { getMyMonitoringStatus } from '@/services/api/monitoringService';
import { DriverProfilePanel } from '@/components/drivers/DriverProfilePanel';
import { DriverCameraPanel } from '@/components/drivers/DriverCameraPanel';
import { DriverLocationControl } from '@/components/drivers/DriverLocationControl';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, type TableColumn } from '@/components/ui/Table';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { formatDateTime } from '@/utils/formatDate';
import { incidentStatusTone, severityTone } from '@/utils/statusColors';
import { MONITORING_EVENT_LABELS } from '@/utils/constants';
import { startContinuousAlarm, stopContinuousAlarm } from '@/utils/audioAlert';
import type { DriverMonitoringStatus, MonitoringEvent } from '@/types';
import type { Trip } from '@/types';
import type { VehicleLocation } from '@/types';

const signalLabels = [
  ['eyeState', 'Eyes'], ['drowsinessLevel', 'Drowsiness'], ['yawnStatus', 'Yawning'], ['phoneUseStatus', 'Phone use'], ['distractionStatus', 'Attention'],
] as const;

export default function DriverDashboardPage() {
  const { data: driver, status, error, refetch } = useAsyncData(() => getMyDriverProfile(), []);
  const { data: trips, refetch: refreshTrips } = useAsyncData(() => getMyTrips(), []);
  const { data: incidents, refetch: refreshIncidents } = useAsyncData(() => getMyIncidents(), []);
  const { data: vehicle, refetch: refreshVehicle } = useAsyncData(() => getAssignedVehicle(), []);
  const { data: location, status: locationStatus, refetch: refreshLocation } = useAsyncData(() => getMyVehicleLocation(), []);
  const { data: fetchedMonitoring, refetch: refreshMonitoring } = useAsyncData(() => getMyMonitoringStatus(driver?.id), [driver?.id]);
  const [sessionMonitoring, setSessionMonitoring] = useState<DriverMonitoringStatus>();
  const [latestSafetyEvent, setLatestSafetyEvent] = useState<MonitoringEvent>();
  const [liveLocation, setLiveLocation] = useState<VehicleLocation>();
  useEffect(() => {
    const timer = window.setInterval(() => {
      setLiveLocation((current) => current && Date.now() - new Date(current.timestamp).getTime() > current.staleAfterSeconds * 1000
        ? { ...current, gpsStatus: 'stale' }
        : current);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);
  const monitoring = sessionMonitoring ?? fetchedMonitoring;

  // These endpoints are scoped by the backend to the signed-in driver. A modest
  // polling interval keeps the dashboard current while avoiding fleet-wide queries.
  useEffect(() => {
    const timer = window.setInterval(() => {
      refreshTrips();
      refreshIncidents();
      refreshVehicle();
      refreshLocation();
      refreshMonitoring();
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [refreshTrips, refreshIncidents, refreshVehicle, refreshLocation, refreshMonitoring]);

  useEffect(() => {
    const active = (monitoring?.source === 'live' || monitoring?.source === 'browser_live') && (monitoring.cameraStatus === 'active' || monitoring.cameraStatus === 'browser_active');
    const reason = monitoring?.drowsinessLevel === 'warning' || monitoring?.drowsinessLevel === 'critical' || monitoring?.eyeState === 'warning' || monitoring?.eyeState === 'critical'
      ? 'eyes_closed'
      : monitoring?.phoneUseStatus === 'warning' || monitoring?.phoneUseStatus === 'critical'
        ? 'phone_use'
        : monitoring?.distractionStatus === 'warning' || monitoring?.distractionStatus === 'critical'
          ? 'distraction' : null;
    if (active && reason) startContinuousAlarm(reason);
    else stopContinuousAlarm();
    return () => stopContinuousAlarm();
  }, [monitoring]);

  if (status === 'loading') return <LoadingState label="Loading your dashboard…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unable to load driver profile'} onRetry={refetch} />;
  if (!driver) return <ErrorState message="No driver profile is linked to this account." onRetry={refetch} />;

  const activeTrip = trips?.find((trip) => trip.status === 'in-progress');
  const tripColumns: TableColumn<Trip>[] = [
    { key: 'when', header: 'Started', render: (row) => formatDateTime(row.startTime) },
    { key: 'route', header: 'Route', render: (row) => `${row.startLocation ?? '—'} → ${row.endLocation ?? '—'}` },
    { key: 'vehicle', header: 'Vehicle', render: (row) => row.vehiclePlate ?? row.vehicleCode ?? '—' },
    { key: 'distance', header: 'Distance', render: (row) => `${row.distanceKm ?? 0} km` },
    { key: 'status', header: 'Status', render: (row) => <Badge label={row.status} tone={row.status === 'in-progress' ? 'info' : 'neutral'} /> },
    { key: 'incidents', header: 'Events', render: (row) => String(row.incidentCount ?? 0) },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Welcome back, {driver.name}</h2>
          <p className="mt-1 text-sm text-text-muted">Your driving status, vehicle, safety signals, and recent trips.</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted"><Wifi size={14} className="text-status-success-text" /> Dashboard refreshes every 10 seconds</div>
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Metric icon={Route} label="Current trip" value={activeTrip ? 'In progress' : 'No active trip'} detail={activeTrip?.startLocation ?? 'Ready for your next trip'} tone={activeTrip ? 'blue' : 'neutral'} />
        <Metric icon={Gauge} label="Safety score" value={`${driver.safetyScore}/100`} detail="Your current fleet score" tone={driver.safetyScore >= 80 ? 'green' : 'amber'} />
        <Metric icon={AlertTriangle} label="My incidents" value={String(incidents?.length ?? 0)} detail="Recorded safety events" tone={(incidents?.length ?? 0) > 0 ? 'red' : 'green'} />
        <Metric icon={Timer} label="Completed trips" value={String(driver.totalTrips)} detail={`${driver.totalDistanceKm.toLocaleString()} km total distance`} tone="blue" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <DriverCameraPanel driverId={driver.id} onMonitoringUpdate={setSessionMonitoring} onSafetyEvents={(events) => { setLatestSafetyEvent(events[0]); refreshIncidents(); }} />
          <Card>
            <CardHeader title="Live driving signals" subtitle={monitoring ? `${monitoring.source === 'live' || monitoring.source === 'browser_live' ? 'Live AI' : monitoring.source === 'simulation' ? 'Monitoring simulation' : 'Camera session stopped'} · Updated ${formatDateTime(monitoring.lastUpdated)}` : 'Waiting for an assigned vehicle monitoring feed'} action={<Activity size={17} className="text-brand-blue" />} />
            {monitoring ? <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
                <div className="rounded-md border border-border p-3"><p className="text-xs text-text-muted">Driver presence</p><p className={`mt-2 inline-flex rounded px-2 py-1 text-xs font-semibold ${monitoring.source === 'none' ? 'text-text-muted bg-surface-inset' : monitoring.presenceDetected ? 'text-status-success-text bg-status-success-bg' : 'text-status-warning-text bg-status-warning-bg'}`}>{monitoring.source === 'none' ? 'no signal' : monitoring.presenceDetected ? 'present' : 'not detected'}</p></div>
                {signalLabels.map(([key, label]) => {
                  const value = monitoring[key];
                  const tone = value === 'normal' ? 'text-status-success-text bg-status-success-bg' : value === 'warning' || value === 'critical' ? 'text-status-danger-text bg-status-danger-bg' : 'text-text-muted bg-surface-inset';
                  return <div key={key} className="rounded-md border border-border p-3"><p className="text-xs text-text-muted">{label}</p><p className={`mt-2 inline-flex rounded px-2 py-1 text-xs font-semibold capitalize ${tone}`}>{value.replace('-', ' ')}</p></div>;
                })}
              </div>
              {monitoring.metrics && <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 border-t border-border pt-3 text-xs text-text-muted"><span>Eye ratio: {monitoring.metrics.ear.toFixed(2)}</span><span>Mouth ratio: {monitoring.metrics.mar.toFixed(2)}</span><span>Head turn: {Math.round(monitoring.metrics.headYaw)}°</span><span>Camera: {monitoring.cameraStatus ?? 'unknown'}</span>{monitoring.processingLatencyMs !== undefined && <span>Inference: {monitoring.processingLatencyMs} ms · {monitoring.inferenceFps ?? '—'} fps</span>}</div>}
              {latestSafetyEvent && <div className="mt-4 rounded-md border border-border bg-surface-inset p-3"><p className="text-xs text-text-muted">Latest event from this camera session</p><p className="mt-1 text-sm font-medium text-text-primary">{MONITORING_EVENT_LABELS[latestSafetyEvent.type] ?? latestSafetyEvent.type} · {latestSafetyEvent.severity}</p><p className="mt-1 text-xs text-text-muted">{formatDateTime(latestSafetyEvent.timestamp)}</p></div>}
              {monitoring.source !== 'live' && monitoring.source !== 'browser_live' && <p className="mt-3 text-xs text-text-muted">These are backend monitoring signals. Start the camera above to send frames for live AI analysis.</p>}
            </> : <p className="text-sm text-text-muted">Monitoring signals appear when your account has an assigned vehicle and an active monitoring feed.</p>}
          </Card>
          <Card>
            <CardHeader title="My trips" subtitle={`${trips?.length ?? 0} recorded`} />
            <Table columns={tripColumns} rows={trips ?? []} getRowId={(row) => row.id} emptyMessage="No trips recorded for your account yet." />
          </Card>
        </div>

        <div className="space-y-6">
          <DriverProfilePanel driver={driver} vehicle={vehicle ?? undefined} />
          <DriverLocationControl driverId={driver.id} vehicleId={vehicle?.id} onLocation={setLiveLocation} />
          <Card>
            <CardHeader title="Assigned vehicle GPS" subtitle={liveLocation?.vehicleId ?? location?.vehicleId ?? vehicle?.id ?? 'Current location'} action={<MapPin size={16} className="text-brand-blue" />} />
            {(liveLocation ?? location) ? <div className="grid grid-cols-2 gap-4 text-sm">
              <Info label="Latitude" value={(liveLocation ?? location)!.lat.toFixed(5)} /><Info label="Longitude" value={(liveLocation ?? location)!.lng.toFixed(5)} />
              <Info label="Speed" value={(liveLocation ?? location)!.speedKmh == null ? '—' : `${Math.round((liveLocation ?? location)!.speedKmh!)} km/h`} /><Info label="Updated" value={formatDateTime((liveLocation ?? location)!.timestamp)} />
              <Info label="Source" value={(liveLocation ?? location)!.gpsStatus === 'live' ? 'LIVE GPS' : (liveLocation ?? location)!.gpsStatus === 'stale' ? 'STALE POSITION' : 'SIMULATED GPS'} />
              {(liveLocation ?? location)!.accuracyM != null && <Info label="Accuracy" value={`±${Math.round((liveLocation ?? location)!.accuracyM!)} m`} />}
            </div> : <p className="text-sm text-text-muted">{locationStatus === 'loading' ? 'Loading GPS position…' : 'No current GPS signal for your assigned vehicle.'}</p>}
          </Card>
          <Card>
            <CardHeader title="Recent safety events" subtitle={`${incidents?.length ?? 0} recorded`} action={<ShieldCheck size={16} className="text-brand-blue" />} />
            {(incidents ?? []).length === 0 ? <p className="text-sm text-text-muted">No incidents recorded for you. Keep driving safely.</p> : <ul className="space-y-3">
              {(incidents ?? []).slice(0, 6).map((incident) => <li key={incident.id} className="flex items-start justify-between gap-3 border-b border-border pb-3 last:border-0 last:pb-0">
                <div className="min-w-0"><p className="text-sm font-medium text-text-primary">{MONITORING_EVENT_LABELS[incident.type] ?? incident.type}</p><p className="mt-1 text-xs text-text-muted">{formatDateTime(incident.timestamp)} · {incident.location}</p></div>
                <div className="flex shrink-0 flex-col items-end gap-1"><Badge label={incident.severity} tone={severityTone(incident.severity)} /><Badge label={incident.status} tone={incidentStatusTone(incident.status)} /></div>
              </li>)}
            </ul>}
          </Card>
        </div>
      </div>
    </div>
  );
}

function Metric({ icon: Icon, label, value, detail, tone }: { icon: typeof Route; label: string; value: string; detail: string; tone: 'blue' | 'green' | 'amber' | 'red' | 'neutral' }) {
  const colors = { blue: 'text-blue-500 bg-blue-500/10', green: 'text-emerald-500 bg-emerald-500/10', amber: 'text-amber-500 bg-amber-500/10', red: 'text-red-500 bg-red-500/10', neutral: 'text-text-muted bg-surface-inset' };
  return <Card className="min-w-0"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="text-xs text-text-muted">{label}</p><p className="mt-2 truncate text-xl font-semibold text-text-primary">{value}</p></div><span className={`rounded-md p-2 ${colors[tone]}`}><Icon size={17} /></span></div><p className="mt-2 truncate text-xs text-text-muted">{detail}</p></Card>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs text-text-muted">{label}</p><p className="mt-1 font-medium text-text-primary">{value}</p></div>;
}
