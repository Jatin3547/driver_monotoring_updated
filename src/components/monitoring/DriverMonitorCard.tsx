import { useState, useRef, useEffect } from 'react';
import { Camera, Eye, Moon, Smartphone, User, UserX, Video, VideoOff, Volume2, VolumeX, AlertTriangle, Activity } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { monitoringSignalTone } from '@/utils/statusColors';
import { timeAgo } from '@/utils/formatDate';
import { startContinuousAlarm, stopContinuousAlarm, isAudioMuted } from '@/utils/audioAlert';
import { useFleetSocketEvent } from '@/hooks/useFleetSocketEvent';
import { useIncidentRecorder } from '@/hooks/useIncidentRecorder';
import { API_BASE_URL } from '@/services/config';
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
  const isPrimaryDriver = status.driverId === 'DRV-001' || status.source === 'live';
  const [useUsbCamera, setUseUsbCamera] = useState(false);
  const [usbError, setUsbError] = useState<string | null>(null);
  const [camStatus, setCamStatus] = useState<'stopped' | 'connecting' | 'live' | 'permission_denied' | 'error'>('stopped');
  const [videoResolution, setVideoResolution] = useState<{ width: number; height: number } | null>(null);
  const [frameCount, setFrameCount] = useState(0);
  const [buzzerTriggered, setBuzzerTriggered] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);

  const {
    recorderState,
    recordingSecondsLeft,
    triggerIncidentRecording,
  } = useIncidentRecorder({
    stream: mediaStream,
    videoRef,
    driverId: status.driverId,
  });

  useFleetSocketEvent<{ id: string; driverId: string }>('incident_created', (inc) => {
    if (isPrimaryDriver && (inc.driverId === status.driverId || status.driverId === 'DRV-001')) {
      triggerIncidentRecording(inc.id, inc.driverId);
    }
  });

  // Continuous in-cab acoustic wake-up buzzer alarm:
  // Keeps beeping non-stop until the driver wakes up / opens eyes, puts phone down, or looks straight!
  useEffect(() => {
    if (!isPrimaryDriver) {
      stopContinuousAlarm();
      setBuzzerTriggered(false);
      return;
    }

    const isEyesClosed =
      status.drowsinessLevel === 'critical' ||
      status.drowsinessLevel === 'warning' ||
      status.eyeState === 'critical' ||
      status.eyeState === 'warning';

    const isPhoneUse =
      status.phoneUseStatus === 'critical' ||
      status.phoneUseStatus === 'warning';

    const isDistracted =
      status.distractionStatus === 'critical' ||
      status.distractionStatus === 'warning';

    const shouldAlarm = isEyesClosed || isPhoneUse || isDistracted;

    if (shouldAlarm) {
      setBuzzerTriggered(true);
      const reason = isEyesClosed
        ? 'eyes_closed'
        : isPhoneUse
        ? 'phone_use'
        : 'distraction';
      startContinuousAlarm(reason);
    } else {
      setBuzzerTriggered(false);
      stopContinuousAlarm();
    }

    return () => {
      stopContinuousAlarm();
    };
  }, [
    isPrimaryDriver,
    status.drowsinessLevel,
    status.eyeState,
    status.phoneUseStatus,
    status.distractionStatus,
  ]);

  // Handle camera permission and MediaStream acquisition
  const startUsbCamera = async () => {
    try {
      setUsbError(null);
      setCamStatus('connecting');

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access requires HTTPS or localhost context in browser');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 15 },
        },
        audio: false,
      });

      streamRef.current = stream;
      setMediaStream(stream);
      setUseUsbCamera(true);
      setCamStatus('live');
    } catch (err: unknown) {
      let msg = 'Failed to open camera stream';
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          msg = 'Camera permission denied. Please enable camera access in browser site settings.';
          setCamStatus('permission_denied');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          msg = 'No camera or webcam device found on this machine.';
          setCamStatus('error');
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          msg = 'Camera is occupied by another app (e.g., Zoom, Teams). Please close it and retry.';
          setCamStatus('error');
        } else {
          msg = `Camera error: ${err.message}`;
          setCamStatus('error');
        }
      } else if (err instanceof Error) {
        msg = err.message;
        setCamStatus('error');
      }
      setUsbError(msg);
      setUseUsbCamera(false);
    }
  };

  // Safely attach streamRef to videoRef once video element mounts in DOM
  useEffect(() => {
    if (!useUsbCamera || !streamRef.current) return;

    const video = videoRef.current;
    if (video) {
      video.srcObject = streamRef.current;
      video.play().then(() => {
        setCamStatus('live');
      }).catch(() => {
        // Browser autoplay restriction handling
      });
    }
  }, [useUsbCamera]);

  // Auto-start camera on mount for active live driver to engage 5s rolling buffer
  useEffect(() => {
    if (isPrimaryDriver && !useUsbCamera && camStatus === 'stopped') {
      startUsbCamera();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPrimaryDriver]);

  const stopUsbCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setMediaStream(null);
    setUseUsbCamera(false);
    setCamStatus('stopped');
    setVideoResolution(null);
    setFrameCount(0);
  };

  // Frame processing and upload loop when USB camera is active
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
              await fetch(`${API_BASE_URL}/monitoring/camera-frame`, {
                method: 'POST',
                body: blob,
                headers: { 'Content-Type': 'image/jpeg' },
              });
              setFrameCount((prev) => prev + 1);
            } catch {
              // Frame dropped or server offline
            }
          },
          'image/jpeg',
          0.7
        );
      } catch {
        // Video render glitch
      }
    }, 70); // ~14 FPS

    return () => {
      isStreaming = false;
      window.clearInterval(intervalId);
    };
  }, [useUsbCamera]);

  // Clean up media tracks on unmount
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
        isPrimaryDriver ? 'border-primary ring-2 ring-primary/20 shadow-md' : 'border-border'
      }`}
    >
      <div className="aspect-video bg-surface-inset flex items-center justify-center relative overflow-hidden">
        {useUsbCamera ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            onLoadedMetadata={(e) => {
              const v = e.currentTarget;
              setVideoResolution({ width: v.videoWidth, height: v.videoHeight });
              setCamStatus('live');
            }}
            className="w-full h-full object-cover bg-black"
          />
        ) : isPrimaryDriver && status.source === 'live' ? (
          <img
            src={`${API_BASE_URL}/monitoring/video-feed`}
            alt="Live In-Cab Camera Feed"
            className="w-full h-full object-cover bg-black"
            onError={() => setUsbError('Backend video stream unavailable. Click "Use USB / Laptop Camera" below.')}
          />
        ) : (
          <Camera size={32} className="text-text-muted opacity-40" />
        )}

        {/* Pulsing Alarm Banner when Continuous Wake-Up Buzzer is Active */}
        {buzzerTriggered && isPrimaryDriver && (
          <div className="absolute top-0 left-0 right-0 bg-red-600 text-white text-[11px] font-bold py-1 px-3 flex items-center justify-between shadow-lg animate-pulse z-30">
            <span className="flex items-center gap-1.5 tracking-wide">
              <AlertTriangle size={13} className="text-yellow-300 animate-bounce" />
              {status.eyeState === 'critical' || status.drowsinessLevel === 'critical' || status.eyeState === 'warning'
                ? '🚨 SLEEP DETECTED / EYES CLOSED — WAKE UP!'
                : status.phoneUseStatus === 'critical' || status.phoneUseStatus === 'warning'
                ? '📱 PHONE USE DETECTED — PUT PHONE DOWN!'
                : '⚠️ DRIVER DISTRACTED — LOOK AT ROAD!'}
            </span>
            <span className="text-[10px] bg-black/40 px-1.5 py-0.5 rounded uppercase">ALARM ACTIVE</span>
          </div>
        )}

        {/* Video Overlay Diagnostics Badge */}
        <span className="absolute top-2 left-2 text-[10px] font-medium bg-black/75 text-white px-2 py-0.5 rounded flex items-center gap-1.5 shadow-sm backdrop-blur-xs">
          {useUsbCamera ? (
            <>
              <span className={`w-2 h-2 rounded-full ${camStatus === 'live' ? 'bg-status-success-text animate-pulse' : 'bg-status-warning-text'}`} />
              USB WEBCAM {camStatus.toUpperCase()} {videoResolution ? `(${videoResolution.width}x${videoResolution.height})` : ''}
            </>
          ) : isPrimaryDriver && status.source === 'live' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-status-success-text animate-pulse" />
              BACKEND CAMERA FEED
            </>
          ) : status.isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-status-info-text" />
              SIMULATED TELEMETRY
            </>
          ) : (
            'NO SIGNAL'
          )}
        </span>

        {/* Evidence Recording Overlays */}
        {recorderState === 'recording_incident' && (
          <div className="absolute bottom-2 left-2 bg-red-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1.5 shadow animate-pulse z-20">
            <span className="w-2 h-2 rounded-full bg-white animate-ping" />
            REC EVIDENCE CLIP ({recordingSecondsLeft}s)
          </div>
        )}
        {recorderState === 'uploading' && (
          <div className="absolute bottom-2 left-2 bg-blue-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1.5 shadow animate-pulse z-20">
            <Activity size={10} className="animate-spin" />
            SAVING MP4 EVIDENCE...
          </div>
        )}
        {recorderState === 'buffering' && (
          <div className="absolute bottom-2 left-2 bg-black/60 text-emerald-400 text-[9px] font-medium px-1.5 py-0.5 rounded flex items-center gap-1 z-10 backdrop-blur-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            5s Rolling Buffer
          </div>
        )}

        <span
          className={`absolute top-2 right-2 w-2 h-2 rounded-full ${status.isOnline ? 'bg-status-success-text' : 'bg-status-danger-text'}`}
        />
      </div>

      {/* Camera Diagnostics & Controls Toolbar */}
      {isPrimaryDriver && (
        <div className="px-3 py-2 flex items-center justify-between border-b border-border bg-surface-muted/40 text-[11px]">
          <div className="flex items-center gap-1.5 text-text-muted">
            {useUsbCamera && frameCount > 0 ? (
              <span className="text-status-success-text flex items-center gap-1">
                <Activity size={12} className="animate-spin" /> AI Ingestion Active ({frameCount} frames)
              </span>
            ) : (
              <span>{useUsbCamera ? 'Webcam active' : 'Click to stream local laptop/USB webcam'}</span>
            )}
          </div>
          <button
            type="button"
            onClick={useUsbCamera ? stopUsbCamera : startUsbCamera}
            className={`font-medium px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors cursor-pointer ${
              useUsbCamera
                ? 'bg-status-danger-bg text-status-danger-text border border-status-danger-border hover:bg-status-danger-bg/80'
                : 'bg-primary text-white hover:bg-primary/90'
            }`}
          >
            {useUsbCamera ? (
              <>
                <VideoOff size={12} /> Stop Camera
              </>
            ) : (
              <>
                <Video size={12} /> Use USB / Laptop Camera
              </>
            )}
          </button>
        </div>
      )}

      {/* Human Readable User Error Messages */}
      {usbError && (
        <div className="px-4 py-2 text-[11px] bg-status-danger-bg text-status-danger-text border-b border-status-danger-border font-medium flex items-center justify-between">
          <span>{usbError}</span>
          <button type="button" onClick={() => setUsbError(null)} className="text-xs underline ml-2 cursor-pointer">
            Dismiss
          </button>
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
