import { useState, useRef, useEffect, useCallback } from 'react';
import { Camera, Eye, Moon, Smartphone, User, UserX, AlertTriangle, Activity, Wifi, RefreshCw, CheckCircle2, XCircle, Volume2, VolumeX } from 'lucide-react';
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

  // Camera selection: 'webcam' (Laptop / USB Webcam) vs 'droidcam' (DroidCam Wi-Fi)
  const [cameraMode, setCameraMode] = useState<'webcam' | 'droidcam'>(() => {
    return (localStorage.getItem('fleetguard_camera_mode') as 'webcam' | 'droidcam') || 'webcam';
  });

  const [camStatus, setCamStatus] = useState<'stopped' | 'connecting' | 'live' | 'permission_denied' | 'error'>('stopped');
  const [videoResolution, setVideoResolution] = useState<{ width: number; height: number } | null>(null);
  const [frameCount, setFrameCount] = useState(0);
  const [buzzerTriggered, setBuzzerTriggered] = useState(false);
  const [usbError, setUsbError] = useState<string | null>(null);
  const [droidCamError, setDroidCamError] = useState<string | null>(null);
  const [isSplashDetected, setIsSplashDetected] = useState(false);
  const [isSwitchingCamera, setIsSwitchingCamera] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const droidCamImgRef = useRef<HTMLImageElement | null>(null);
  const droidCamCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);

  const isLiveFeedValid = !isSplashDetected && (
    (cameraMode === 'webcam' && camStatus === 'live') ||
    (cameraMode === 'droidcam' && !droidCamError)
  );

  const {
    recorderState,
    recordingSecondsLeft,
    triggerIncidentRecording,
  } = useIncidentRecorder({
    stream: mediaStream,
    videoRef,
    driverId: status.driverId,
    isLiveFeedValid,
    onUploadSuccess: () => {
      setUsbError(null);
      setDroidCamError(null);
    },
    onUploadError: (err) => {
      if (cameraMode === 'webcam') {
        setUsbError(err.message);
      } else {
        setDroidCamError(err.message);
      }
    },
  });

  useFleetSocketEvent<{ id: string; driverId: string }>('incident_created', (inc) => {
    if (isPrimaryDriver && (inc.driverId === status.driverId || status.driverId === 'DRV-001')) {
      triggerIncidentRecording(inc.id, inc.driverId);
    }
  });

  // Continuous in-cab acoustic wake-up buzzer alarm
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

  // Clean release of USB camera tracks
  const stopUsbCameraTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Start Laptop / USB Webcam
  const startWebcam = useCallback(async () => {
    try {
      setIsSwitchingCamera(true);
      setUsbError(null);
      setCamStatus('connecting');

      // Stop any existing tracks
      stopUsbCameraTracks();

      // Tell backend to release any hardware locks so browser can access webcam exclusively
      try {
        await fetch(`${API_BASE_URL}/monitoring/select-source`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sourceType: 'webcam' }),
        });
      } catch {
        // Backend offline or starting
      }

      await new Promise((r) => setTimeout(r, 150));

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access requires HTTPS or localhost in your browser.');
      }

      // Query available devices to avoid virtual DroidCam if physical webcam exists
      let preferredDeviceId: string | undefined = undefined;
      if (navigator.mediaDevices.enumerateDevices) {
        try {
          const allDevs = await navigator.mediaDevices.enumerateDevices();
          const videoDevs = allDevs.filter((d) => d.kind === 'videoinput');
          const physicalCam = videoDevs.find((d) => !d.label.toLowerCase().includes('droidcam') && d.label !== '');
          if (physicalCam) {
            preferredDeviceId = physicalCam.deviceId;
          }
        } catch {
          // Ignore
        }
      }

      const constraints: MediaStreamConstraints = {
        video: preferredDeviceId
          ? { deviceId: { exact: preferredDeviceId }, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } }
          : { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
        audio: false,
      };

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch {
        // Fallback to generic video
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }

      streamRef.current = stream;
      setMediaStream(stream);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
      }

      setCamStatus('live');
      setIsSplashDetected(false);
    } catch (err: unknown) {
      let msg = 'Failed to open laptop webcam.';
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          msg = 'Camera permission denied. Please allow camera access in browser site settings.';
          setCamStatus('permission_denied');
        } else if (err.name === 'NotFoundError') {
          msg = 'No physical webcam found on this device.';
          setCamStatus('error');
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          msg = 'Camera is occupied by another app (e.g. Zoom, Teams). Please close it and retry.';
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
      setCamStatus('error');
    } finally {
      setIsSwitchingCamera(false);
    }
  }, [stopUsbCameraTracks]);

  // Connect to DroidCam Wi-Fi
  const startDroidCam = useCallback(async () => {
    try {
      setIsSwitchingCamera(true);
      setDroidCamError(null);
      setIsSplashDetected(false);

      // Cleanly release local webcam first
      stopUsbCameraTracks();

      // Probe DroidCam Wi-Fi endpoint (192.168.0.4:4747)
      const probeRes = await fetch(`${API_BASE_URL}/monitoring/probe-network-camera?url=http://192.168.0.4:4747/video`);
      const probeData = await probeRes.json();

      if (!probeData.reachable) {
        setDroidCamError('Could not reach DroidCam at 192.168.0.4:4747. Ensure DroidCam is running on your phone and connected to the same Wi-Fi.');
      }

      // Tell backend to switch AI camera reader to DroidCam HTTP stream
      await fetch(`${API_BASE_URL}/monitoring/select-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceType: 'droidcam',
          url: 'http://192.168.0.4:4747/video',
        }),
      });

      setCamStatus('live');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setDroidCamError(`DroidCam connection failed: ${msg}`);
      setCamStatus('error');
    } finally {
      setIsSwitchingCamera(false);
    }
  }, [stopUsbCameraTracks]);

  // Handle switching between the two clear camera options
  const handleSwitchCamera = useCallback((newMode: 'webcam' | 'droidcam') => {
    setCameraMode(newMode);
    localStorage.setItem('fleetguard_camera_mode', newMode);
    setUsbError(null);
    setDroidCamError(null);
    setIsSplashDetected(false);

    if (newMode === 'webcam') {
      startWebcam();
    } else {
      startDroidCam();
    }
  }, [startWebcam, startDroidCam]);

  // Auto-start active camera on initial mount
  useEffect(() => {
    if (!isPrimaryDriver) return;
    const initialMode = (localStorage.getItem('fleetguard_camera_mode') as 'webcam' | 'droidcam') || 'webcam';
    if (initialMode === 'webcam') {
      startWebcam();
    } else {
      startDroidCam();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPrimaryDriver]);

  // Loop 1: When in webcam mode, upload frames from <video> to /api/monitoring/camera-frame for live AI
  useEffect(() => {
    if (cameraMode !== 'webcam' || camStatus !== 'live') return;

    let isStreaming = true;
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    let consecutiveSplashCount = 0;

    const intervalId = window.setInterval(() => {
      const video = videoRef.current;
      if (!video || video.readyState < 2 || !isStreaming) return;

      try {
        ctx?.drawImage(video, 0, 0, 640, 480);

        // Check for DroidCam virtual camera splash screen
        if (ctx) {
          const imgData = ctx.getImageData(0, 0, 640, 480).data;
          let blackPixelCount = 0;
          let totalLuminance = 0;
          let samples = 0;
          const step = 640 * 4 * 16 + 4 * 16;
          for (let i = 0; i < imgData.length; i += step) {
            const r = imgData[i];
            const g = imgData[i + 1];
            const b = imgData[i + 2];
            totalLuminance += 0.299 * r + 0.587 * g + 0.114 * b;
            if (r <= 15 && g <= 15 && b <= 15) blackPixelCount++;
            samples++;
          }
          const blackRatio = samples > 0 ? blackPixelCount / samples : 0;
          const avgLuminance = samples > 0 ? totalLuminance / samples : 0;

          if (blackRatio > 0.985 && avgLuminance < 1.5) {
            consecutiveSplashCount++;
            if (consecutiveSplashCount >= 3) setIsSplashDetected(true);
          } else {
            consecutiveSplashCount = 0;
            setIsSplashDetected(false);
          }
        }

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
              // Ignore network drops
            }
          },
          'image/jpeg',
          0.7
        );
      } catch {
        // Glitch handling
      }
    }, 70); // ~14 FPS

    return () => {
      isStreaming = false;
      window.clearInterval(intervalId);
    };
  }, [cameraMode, camStatus]);

  // Loop 2: When in DroidCam Wi-Fi mode, render backend MJPEG feed onto hidden canvas and provide MediaStream to recorder
  useEffect(() => {
    if (cameraMode !== 'droidcam') return;

    let isRunning = true;
    const canvas = droidCamCanvasRef.current || document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    droidCamCanvasRef.current = canvas;
    const ctx = canvas.getContext('2d');

    // Produce MediaStream for useIncidentRecorder
    try {
      if (typeof canvas.captureStream === 'function') {
        const stream = canvas.captureStream(15);
        setMediaStream(stream);
      }
    } catch {
      // Capture stream fallback
    }

    const intervalId = window.setInterval(() => {
      if (!isRunning) return;
      const img = droidCamImgRef.current;
      if (img && img.complete && img.naturalWidth > 0 && ctx) {
        try {
          ctx.drawImage(img, 0, 0, 640, 480);
          setFrameCount((prev) => prev + 1);
        } catch {
          // Ignore draw glitches
        }
      }
    }, 66); // ~15 FPS

    return () => {
      isRunning = false;
      window.clearInterval(intervalId);
    };
  }, [cameraMode]);

  // Clean up on component unmount
  useEffect(() => {
    return () => {
      stopUsbCameraTracks();
    };
  }, [stopUsbCameraTracks]);

  return (
    <div
      className={`bg-surface border rounded-lg overflow-hidden flex flex-col transition-all ${
        isPrimaryDriver ? 'border-primary ring-2 ring-primary/20 shadow-md' : 'border-border'
      }`}
    >
      {/* Video Preview Container */}
      <div className="aspect-video bg-surface-inset flex items-center justify-center relative overflow-hidden">
        {cameraMode === 'webcam' ? (
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
        ) : (
          <img
            ref={droidCamImgRef}
            src={`${API_BASE_URL}/monitoring/video-feed`}
            alt="DroidCam Wi-Fi Live Feed"
            crossOrigin="anonymous"
            onLoad={() => {
              setCamStatus('live');
              setDroidCamError(null);
            }}
            onError={() => {
              setDroidCamError('DroidCam stream unreachable at 192.168.0.4:4747. Ensure the app is running on your phone.');
            }}
            className="w-full h-full object-cover bg-black"
          />
        )}

        {/* Hidden canvas for DroidCam MediaStream evidence recording */}
        <canvas ref={droidCamCanvasRef} width={640} height={480} className="hidden" />

        {/* In-Cab Acoustic Wake-Up Alarm Banner */}
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

        {/* Video Overlay Diagnostic Pill */}
        <span className="absolute top-2 left-2 text-[10px] font-medium bg-black/75 text-white px-2 py-0.5 rounded flex items-center gap-1.5 shadow-sm backdrop-blur-xs z-20">
          <span
            className={`w-2 h-2 rounded-full ${
              isSplashDetected || usbError || droidCamError
                ? 'bg-status-danger-text animate-ping'
                : camStatus === 'live'
                ? 'bg-status-success-text animate-pulse'
                : 'bg-status-warning-text'
            }`}
          />
          {cameraMode === 'webcam'
            ? `LAPTOP WEBCAM ${camStatus.toUpperCase()}`
            : 'DROIDCAM (192.168.0.4:4747)'}
          {cameraMode === 'webcam' && videoResolution
            ? ` (${videoResolution.width}x${videoResolution.height})`
            : ''}
        </span>

        {/* Splash Screen Detected Warning */}
        {isSplashDetected && (
          <div className="absolute inset-x-0 bottom-0 bg-red-950/95 border-t-2 border-red-500 text-white p-3 z-30 flex flex-col gap-1.5 shadow-lg backdrop-blur-xs">
            <div className="flex items-center gap-2 font-bold text-xs text-red-200">
              <AlertTriangle size={15} className="text-yellow-400 shrink-0 animate-bounce" />
              <span>DROIDCAM SPLASH SCREEN DETECTED</span>
            </div>
            <p className="text-[11px] text-gray-200 leading-snug">
              The camera feed displays "Start DroidCam" placeholder text instead of live driver footage. Evidence recording is paused. Start DroidCam on your phone or switch to Laptop Webcam.
            </p>
            <button
              type="button"
              onClick={() => handleSwitchCamera('webcam')}
              className="mt-1 self-start px-2.5 py-1 bg-primary hover:bg-primary/90 text-white rounded text-[11px] font-medium transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <Camera size={12} /> Switch to Laptop / USB Webcam
            </button>
          </div>
        )}

        {/* Evidence Recording Status Indicators */}
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

      {/* Two-Option Camera Selector Toolbar */}
      {isPrimaryDriver && (
        <div className="px-3 py-2 flex items-center justify-between border-b border-border bg-surface-muted/50 text-[11px] gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-text-secondary">
            <Activity size={12} className={camStatus === 'live' ? 'text-status-success-text animate-spin' : 'text-text-muted'} />
            <span className="font-medium">Active Source:</span>
            <span className="text-text-primary font-semibold">
              {cameraMode === 'webcam' ? 'Laptop / USB Webcam' : 'DroidCam (Wi-Fi 192.168.0.4)'}
            </span>
          </div>

          {/* Simple, Clear Two-Option Camera Selector */}
          <div className="inline-flex rounded-md shadow-2xs border border-border p-0.5 bg-surface">
            <button
              type="button"
              disabled={isSwitchingCamera}
              onClick={() => handleSwitchCamera('webcam')}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
                cameraMode === 'webcam'
                  ? 'bg-primary text-white shadow-xs'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-muted'
              }`}
            >
              <Camera size={12} />
              Laptop / USB Webcam
            </button>
            <button
              type="button"
              disabled={isSwitchingCamera}
              onClick={() => handleSwitchCamera('droidcam')}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
                cameraMode === 'droidcam'
                  ? 'bg-primary text-white shadow-xs'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-muted'
              }`}
            >
              <Wifi size={12} />
              DroidCam (Wi-Fi)
            </button>
          </div>
        </div>
      )}

      {/* DroidCam Connection Error Banner with Quick Switch */}
      {droidCamError && cameraMode === 'droidcam' && (
        <div className="px-4 py-2.5 text-[11px] bg-status-danger-bg text-status-danger-text border-b border-status-danger-border font-medium flex items-center justify-between gap-2 flex-wrap animate-in fade-in duration-150">
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={13} className="shrink-0 text-red-500" />
            <span>{droidCamError}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleSwitchCamera('droidcam')}
              className="px-2 py-0.5 bg-status-danger-text text-white rounded text-[10px] font-semibold hover:opacity-90 cursor-pointer flex items-center gap-1"
            >
              <RefreshCw size={10} /> Retry
            </button>
            <button
              type="button"
              onClick={() => handleSwitchCamera('webcam')}
              className="px-2 py-0.5 bg-primary text-white rounded text-[10px] font-semibold hover:opacity-90 cursor-pointer flex items-center gap-1"
            >
              <Camera size={10} /> Switch to Laptop Webcam
            </button>
          </div>
        </div>
      )}

      {/* Webcam Error Banner with Retry */}
      {usbError && cameraMode === 'webcam' && (
        <div className="px-4 py-2.5 text-[11px] bg-status-danger-bg text-status-danger-text border-b border-status-danger-border font-medium flex items-center justify-between gap-2 flex-wrap animate-in fade-in duration-150">
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={13} className="shrink-0 text-red-500" />
            <span>{usbError}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => startWebcam()}
              className="px-2 py-0.5 bg-status-danger-text text-white rounded text-[10px] font-semibold hover:opacity-90 cursor-pointer flex items-center gap-1"
            >
              <RefreshCw size={10} /> Retry
            </button>
            <button
              type="button"
              onClick={() => handleSwitchCamera('droidcam')}
              className="px-2 py-0.5 bg-primary text-white rounded text-[10px] font-semibold hover:opacity-90 cursor-pointer flex items-center gap-1"
            >
              <Wifi size={10} /> Switch to DroidCam
            </button>
          </div>
        </div>
      )}

      {/* Driver Information & Real-time AI Metrics */}
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
