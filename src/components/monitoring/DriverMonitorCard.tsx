import { useState, useRef, useEffect } from 'react';
import { Camera, Eye, Moon, Smartphone, User, UserX, Video, VideoOff, Volume2, VolumeX, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { monitoringSignalTone } from '@/utils/statusColors';
import { timeAgo } from '@/utils/formatDate';
import { playImmediateDriverWarning, isAudioMuted } from '@/utils/audioAlert';
import type { Driver, DriverMonitoringStatus, Vehicle } from '@/types';

interface Props {
  status: DriverMonitoringStatus;
  driver?: Driver;
  vehicle?: Vehicle;
}

const signalRows: { key: keyof DriverMonitoringStatus; label: string; icon: typeof Eye }[] = [
  { key: 'eyeState', label: 'Eye state', icon: Eye },
  { key: 'drowsinessLevel', label: 'Drowsiness', icon: Moon },
  { key: 'yawnStatus', label: 'Yawning', icon: User },
  { key: 'phoneUseStatus', label: 'Phone use', icon: Smartphone },
  { key: 'distractionStatus', label: 'Distraction', icon: UserX },
];

export function DriverMonitorCard({ status, driver, vehicle }: Props) {
  const isPrimaryLive = status.source === 'live' && status.driverId === 'DRV-001';
  const [useUsbCamera, setUseUsbCamera] = useState(false);
  const [usbError, setUsbError] = useState<string | null>(null);
  const [buzzerTriggered, setBuzzerTriggered] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Trigger in-cab acoustic buzzer when critical conditions arise
  useEffect(() => {
    const isCritical =
      status.drowsinessLevel === 'critical' ||
      status.eyeState === 'critical' ||
      status.phoneUseStatus === 'critical';

    const isWarning =
      status.yawnStatus === 'warning' ||
      status.distractionStatus === 'warning';

    let resetTimer: ReturnType<typeof setTimeout> | null = null;
    let triggerTimer: ReturnType<typeof setTimeout> | null = null;

    if (isCritical) {
      const sounded = playImmediateDriverWarning('critical');
      if (sounded) {
        triggerTimer = setTimeout(() => setBuzzerTriggered(true), 0);
        resetTimer = setTimeout(() => setBuzzerTriggered(false), 2500);
      }
    } else if (isWarning) {
      const sounded = playImmediateDriverWarning('warning');
      if (sounded) {
        triggerTimer = setTimeout(() => setBuzzerTriggered(true), 0);
        resetTimer = setTimeout(() => setBuzzerTriggered(false), 2000);
      }
    }

    return () => {
      if (triggerTimer) clearTimeout(triggerTimer);
      if (resetTimer) clearTimeout(resetTimer);
    };
  }, [status.drowsinessLevel, status.eyeState, status.phoneUseStatus, status.yawnStatus, status.distractionStatus]);

  const startUsbCamera = async () => {
    try {
      setUsbError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
      }
      setUseUsbCamera(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to open USB camera';
      setUsbError(msg);
      setUseUsbCamera(false);
    }
  };

  const stopUsbCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setUseUsbCamera(false);
  };

  useEffect(() => {
    if (!useUsbCamera) return;

    let isStreaming = true;
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');

    const intervalId = window.setInterval(() => {
      const video = videoRef.current;
      if (!video || video.readyState < 2 || !isStreaming) return;

      try {
        ctx?.drawImage(video, 0, 0, 640, 480);
        canvas.toBlob(
          async (blob) => {
            if (!blob || !isStreaming) return;
            try {
              await fetch('http://127.0.0.1:8000/api/monitoring/camera-frame', {
                method: 'POST',
                body: blob,
                headers: { 'Content-Type': 'image/jpeg' },
              });
            } catch {
              // Frame dropped or server busy
            }
          },
          'image/jpeg',
          0.7
        );
      } catch {
        // Video read glitch
      }
    }, 70); // ~14 FPS

    return () => {
      isStreaming = false;
      window.clearInterval(intervalId);
    };
  }, [useUsbCamera]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return (
    <div
      className={`bg-surface border rounded-lg overflow-hidden flex flex-col transition-all ${
        isPrimaryLive ? 'border-primary ring-2 ring-primary/20 shadow-md' : 'border-border'
      }`}
    >
      <div className="aspect-video bg-surface-inset flex items-center justify-center relative overflow-hidden">
        {isPrimaryLive ? (
          useUsbCamera ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
          ) : (
            <img
              src="http://127.0.0.1:8000/api/monitoring/video-feed"
              alt="Live In-Cab Camera Feed"
              className="w-full h-full object-cover"
            />
          )
        ) : (
          <Camera size={28} className="text-text-muted" />
        )}
        <span className="absolute top-2 left-2 text-[10px] font-medium bg-black/70 text-white px-2 py-0.5 rounded flex items-center gap-1.5 shadow-sm">
          {isPrimaryLive ? (
            useUsbCamera ? (
              <>
                <span className="w-2 h-2 rounded-full bg-status-success-text animate-pulse" />
                USB / WEBCAM ACTIVE
              </>
            ) : status.cameraStatus === 'error' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-status-danger-text" />
                CAMERA OFFLINE
              </>
            ) : status.cameraStatus === 'reconnecting' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-status-warning-text animate-ping" />
                RECONNECTING CAMERA
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-status-danger-text animate-pulse" />
                PRIMARY MONITORED DRIVER
              </>
            )
          ) : status.isOnline ? (
            'SIMULATED'
          ) : (
            'NO SIGNAL'
          )}
        </span>
        <span
          className={`absolute top-2 right-2 w-2 h-2 rounded-full ${status.isOnline ? 'bg-status-success-text' : 'bg-status-danger-text'}`}
        />
      </div>

      {isPrimaryLive && (
        <div className="px-4 pt-2.5 pb-1 flex items-center justify-between border-b border-border bg-surface-muted/30">
          <span className="text-[11px] text-text-muted">
            {useUsbCamera ? 'Streaming from USB/Laptop webcam' : 'Listening for DroidCam / IP stream'}
          </span>
          <button
            type="button"
            onClick={useUsbCamera ? stopUsbCamera : startUsbCamera}
            className={`text-[11px] font-medium px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors cursor-pointer ${
              useUsbCamera
                ? 'bg-status-danger-bg text-status-danger-text border border-status-danger-border hover:bg-status-danger-bg/80'
                : 'bg-primary text-white hover:bg-primary/90'
            }`}
          >
            {useUsbCamera ? (
              <>
                <VideoOff size={12} /> Stop USB Camera
              </>
            ) : (
              <>
                <Video size={12} /> Use USB / Laptop Camera
              </>
            )}
          </button>
        </div>
      )}

      {usbError && (
        <div className="px-4 py-1.5 text-[11px] bg-status-danger-bg text-status-danger-text border-b border-status-danger-border">
          {usbError}
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm font-semibold text-text-primary">{driver?.name ?? status.driverId}</p>
            <p className="text-xs text-text-muted">{vehicle?.plateNumber ?? status.vehicleId}</p>
          </div>
          <div className="flex items-center gap-1.5">
            {isAudioMuted() && (
              <span title="Audio muted for this cab" className="text-text-muted">
                <VolumeX size={14} />
              </span>
            )}
            <Badge
              label={status.presenceDetected ? 'Present' : 'No presence'}
              tone={status.presenceDetected ? 'success' : 'danger'}
            />
          </div>
        </div>

        {buzzerTriggered && (
          <div className="mb-3 px-2.5 py-1.5 bg-status-danger-bg border border-status-danger-border rounded-md text-[11px] font-semibold text-status-danger-text flex items-center justify-between animate-pulse">
            <span className="flex items-center gap-1.5">
              <AlertTriangle size={13} /> IN-CAB BUZZER SOUNDING
            </span>
            <Volume2 size={13} />
          </div>
        )}

        <div className="space-y-2 flex-1">
          {signalRows.map(({ key, label, icon: Icon }) => {
            const value = status[key] as string;
            return (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-text-secondary">
                  <Icon size={13} className="text-text-muted" /> {label}
                </span>
                <Badge label={value.replace('-', ' ')} tone={monitoringSignalTone(value)} dot={false} />
              </div>
            );
          })}
        </div>

        {status.metrics && (
          <div className="mt-3 pt-2.5 border-t border-border grid grid-cols-3 gap-1.5 text-center">
            <div className="bg-surface-muted/60 py-1 px-1 rounded">
              <span className="text-text-muted block text-[10px]">EAR (Eyes)</span>
              <span className="font-semibold text-xs text-text-primary">
                {status.metrics.ear !== undefined ? status.metrics.ear.toFixed(2) : '--'}
              </span>
            </div>
            <div className="bg-surface-muted/60 py-1 px-1 rounded">
              <span className="text-text-muted block text-[10px]">MAR (Mouth)</span>
              <span className="font-semibold text-xs text-text-primary">
                {status.metrics.mar !== undefined ? status.metrics.mar.toFixed(2) : '--'}
              </span>
            </div>
            <div className="bg-surface-muted/60 py-1 px-1 rounded">
              <span className="text-text-muted block text-[10px]">Head Yaw</span>
              <span className="font-semibold text-xs text-text-primary">
                {status.metrics.headYaw !== undefined ? `${status.metrics.headYaw.toFixed(1)}°` : '--'}
              </span>
            </div>
          </div>
        )}

        <p className="text-[11px] text-text-muted mt-3 pt-2 border-t border-border">
          Updated {timeAgo(status.lastUpdated)}
        </p>
      </div>
    </div>
  );
}
