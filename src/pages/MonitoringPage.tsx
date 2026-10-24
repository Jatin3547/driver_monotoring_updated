import { useState, useEffect } from 'react';
import { useAsyncData } from '@/hooks/useAsyncData';
import { getMonitoringStatuses, getMonitoringEvents, getAiStatus } from '@/services/api/monitoringService';
import { getDrivers } from '@/services/api/driverService';
import { getVehicles } from '@/services/api/vehicleService';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { MonitoringStatusGrid } from '@/components/monitoring/MonitoringStatusGrid';
import { EventTimeline } from '@/components/monitoring/EventTimeline';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { Camera, Radio, Volume2, VolumeX, BellRing } from 'lucide-react';
import { playImmediateDriverWarning, isAudioMuted, setAudioMuted, stopContinuousAlarm } from '@/utils/audioAlert';
import type { DriverMonitoringStatus, MonitoringEvent } from '@/types';

export default function MonitoringPage() {
  const { data: initialStatuses, status, error, refetch } = useAsyncData(() => getMonitoringStatuses(), []);
  const { data: initialEvents } = useAsyncData(() => getMonitoringEvents(), []);
  const { data: drivers } = useAsyncData(() => getDrivers(), []);
  const { data: vehicles } = useAsyncData(() => getVehicles(), []);
  const { data: aiStatus } = useAsyncData(() => getAiStatus(), []);

  const [liveStatuses, setLiveStatuses] = useState<DriverMonitoringStatus[] | null>(null);
  const [liveEvents, setLiveEvents] = useState<MonitoringEvent[] | null>(null);
  const [audioMuted, setAudioMutedState] = useState<boolean>(() => isAudioMuted());
  const [lastBeepMessage, setLastBeepMessage] = useState<string | null>(null);

  useEffect(() => {
    const handleSettingsChanged = () => setAudioMutedState(isAudioMuted());
    window.addEventListener('fleetguard_audio_settings_changed', handleSettingsChanged);
    return () => {
      window.removeEventListener('fleetguard_audio_settings_changed', handleSettingsChanged);
      stopContinuousAlarm();
    };
  }, []);

  const statuses = liveStatuses ?? initialStatuses ?? [];
  const events = liveEvents ?? initialEvents ?? [];

  useFleetSocketEvent<DriverMonitoringStatus>('monitoring_update', (update) => {
    setLiveStatuses((prev) => {
      const base = prev ?? initialStatuses ?? [];
      const exists = base.some((s) => s.driverId === update.driverId);
      const updated = exists
        ? base.map((s) => (s.driverId === update.driverId ? update : s))
        : [...base, update];
      return updated.sort((a, b) => {
        const aLive = a.driverId === 'DRV-001' || a.source === 'live';
        const bLive = b.driverId === 'DRV-001' || b.source === 'live';
        if (aLive && !bLive) return -1;
        if (!aLive && bLive) return 1;
        return a.driverId.localeCompare(b.driverId);
      });
    });
  });

  useFleetSocketEvent<MonitoringEvent>('safety_event', (event) => {
    setLiveEvents((prev) => {
      const base = prev ?? initialEvents ?? [];
      if (base.some((e) => e.id === event.id)) return base;
      return [event, ...base].slice(0, 50);
    });

    // Acoustic wake-up buzzer ONLY for live driver on: distraction, phone use, or eyes closed / drowsiness
    const isLiveTarget = event.driverId === 'DRV-001' || event.source === 'live';
    const isTargetEvent = ['drowsiness', 'eye_closure', 'distraction', 'phone_use'].includes(event.type);

    if (isLiveTarget && isTargetEvent) {
      const sounded = playImmediateDriverWarning('critical');
      if (sounded) {
        setLastBeepMessage(`Wake-up alarm sounded: ${event.type.replace('_', ' ').toUpperCase()}`);
        setTimeout(() => setLastBeepMessage(null), 3500);
      }
    }
  });

  const toggleMute = () => {
    const next = !audioMuted;
    setAudioMuted(next);
    setAudioMutedState(next);
  };

  const handleTestBeep = () => {
    playImmediateDriverWarning('test', true);
    setLastBeepMessage('In-cab test chime sounded.');
    setTimeout(() => setLastBeepMessage(null), 3000);
  };

  if (status === 'loading') return <LoadingState label="Connecting to monitoring feeds…" />;
  if (status === 'error') return <ErrorState message={error ?? 'Unknown error'} onRetry={refetch} />;

  const isLive = aiStatus?.activeSource === 'live';

  return (
    <div className="space-y-6">
      {/* Top Banner: Diagnostics & Audio Warning Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface border border-border rounded-lg p-3">
        <div
          className={`flex items-center gap-2 text-xs rounded-md px-3 py-1.5 ${
            isLive
              ? 'bg-status-success-bg border border-status-success-border text-status-success-text'
              : 'bg-status-info-bg border border-status-info-border text-status-info-text'
          }`}
        >
          {isLive ? <Radio size={14} /> : <Camera size={14} />}
          {isLive ? (
            <span>
              <strong>LIVE AI ACTIVE</strong> — OpenCV/MediaPipe/YOLO running (camera #{aiStatus?.cameraIndex})
            </span>
          ) : (
            <span>
              <strong>DEMO / SIMULATION MODE</strong> — Deterministic AI metrics active
            </span>
          )}
        </div>

        {/* Audio Warning Action Bar */}
        <div className="flex items-center gap-2">
          {lastBeepMessage && (
            <span className="text-xs text-status-danger-text bg-status-danger-bg border border-status-danger-border px-2 py-1 rounded animate-pulse flex items-center gap-1">
              <BellRing size={12} /> {lastBeepMessage}
            </span>
          )}
          <button
            type="button"
            onClick={toggleMute}
            className={`text-xs px-2.5 py-1.5 rounded border flex items-center gap-1.5 font-medium transition-colors cursor-pointer ${
              audioMuted
                ? 'bg-status-neutral-bg border-border text-text-muted hover:text-text-primary'
                : 'bg-status-success-bg border-status-success-border text-status-success-text hover:bg-status-success-bg/80'
            }`}
            title={audioMuted ? 'Driver audio buzzer is muted' : 'Driver audio buzzer is active'}
          >
            {audioMuted ? <VolumeX size={13} /> : <Volume2 size={13} />}
            {audioMuted ? 'Buzzer Muted' : 'In-Cab Buzzer Active'}
          </button>
          <button
            type="button"
            onClick={handleTestBeep}
            className="text-xs px-2.5 py-1.5 rounded border border-border bg-surface-inset hover:bg-surface text-text-primary font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Test driver warning speaker tone"
          >
            <BellRing size={13} className="text-brand-blue" />
            Test Beep
          </button>
        </div>
      </div>

      <MonitoringStatusGrid statuses={statuses} drivers={drivers ?? []} vehicles={vehicles ?? []} />

      <EventTimeline events={events} drivers={drivers ?? []} vehicles={vehicles ?? []} />
    </div>
  );
}
