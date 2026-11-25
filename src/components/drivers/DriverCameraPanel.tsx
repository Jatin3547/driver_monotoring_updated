import { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, Circle, ShieldCheck } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { API_BASE_URL } from '@/services/config';
import { getStoredToken } from '@/services/api/authService';
import type { DriverMonitoringStatus } from '@/types';
import type { MonitoringEvent } from '@/types';
import { useIncidentRecorder } from '@/hooks/useIncidentRecorder';

type CameraState = 'off' | 'starting' | 'live' | 'reconnecting' | 'error';

function noSignalStatus(driverId: string, cameraStatus: 'stopped' | 'reconnecting' = 'stopped'): DriverMonitoringStatus {
  return {
    driverId,
    vehicleId: '',
    isOnline: false,
    presenceDetected: false,
    eyeState: 'no-signal',
    drowsinessLevel: 'no-signal',
    yawnStatus: 'no-signal',
    phoneUseStatus: 'no-signal',
    distractionStatus: 'no-signal',
    lastUpdated: new Date().toISOString(),
    source: 'none',
    cameraStatus,
    aiHealth: 'degraded',
  };
}

/** Driver camera preview with authenticated, low-rate frame inference. */
export function DriverCameraPanel({
  onMonitoringUpdate,
  onSafetyEvents,
  driverId,
}: {
  onMonitoringUpdate?: (status: DriverMonitoringStatus | undefined) => void;
  onSafetyEvents?: (events: MonitoringEvent[]) => void;
  driverId: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const sendingFrameRef = useRef(false);
  const sessionStartedRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const frameConfigRef = useRef({ width: 320, height: 240, jpegQuality: 0.55, intervalMs: 500 });
  const [state, setState] = useState<CameraState>('off');
  const [error, setError] = useState<string | null>(null);
  const [framesAccepted, setFramesAccepted] = useState(0);
  const [lastFrameAt, setLastFrameAt] = useState<string | null>(null);
  const [backendResponse, setBackendResponse] = useState('Not connected');
  const [phoneDiagnostics, setPhoneDiagnostics] = useState<DriverMonitoringStatus['phoneDiagnostics']>();
  const [frameMetrics, setFrameMetrics] = useState<Pick<DriverMonitoringStatus, 'inferenceFps' | 'processingLatencyMs' | 'mediaPipeLatencyMs' | 'yoloLatencyMs' | 'averageProcessingLatencyMs' | 'peakProcessingLatencyMs' | 'framesRejected'>>({});
  const recorder = useIncidentRecorder({
    stream: mediaStream,
    videoRef,
    driverId,
    isLiveFeedValid: state === 'live',
    uploadAsDriver: true,
    onUploadSuccess: () => setError(null),
    onUploadError: (cause) => setError(cause.message),
  });

  const stopCamera = () => {
    if (frameTimerRef.current !== null) window.clearTimeout(frameTimerRef.current);
    frameTimerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setMediaStream(null);
    if (sessionStartedRef.current) {
      sessionStartedRef.current = false;
      fetch(`${API_BASE_URL}/monitoring/my-camera-session`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getStoredToken() ?? ''}` },
      }).catch(() => {});
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    onMonitoringUpdate?.(noSignalStatus(driverId));
    setBackendResponse('Camera session stopped.');
    setError(null);
    setState('off');
  };

  const startCamera = async () => {
    setError(null);
    setFramesAccepted(0);
    setLastFrameAt(null);
    setBackendResponse('Starting authenticated camera session…');
    setState('starting');
    try {
      const token = getStoredToken();
      const sessionResponse = await fetch(`${API_BASE_URL}/monitoring/my-camera-session`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token ?? ''}` },
      });
      if (!sessionResponse.ok) {
        const payload = await sessionResponse.json().catch(() => ({}));
        if (sessionResponse.status === 409 && typeof payload.detail === 'string' && payload.detail.includes('already active for this driver account')) {
          sessionStartedRef.current = true;
        } else {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : `Could not start AI session (${sessionResponse.status}).`);
        }
      } else {
        sessionStartedRef.current = true;
        const sessionConfig = await sessionResponse.json().catch(() => ({}));
        frameConfigRef.current = {
          width: sessionConfig.frameWidth ?? 320,
          height: sessionConfig.frameHeight ?? 240,
          jpegQuality: sessionConfig.jpegQuality ?? 0.55,
          intervalMs: sessionConfig.frameIntervalMs ?? 500,
        };
      }
      setBackendResponse('Session ready; waiting for browser camera frames.');
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera access requires HTTPS or localhost.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      setMediaStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState('live');
      reconnectAttemptsRef.current = 0;

      const sendNextFrame = async () => {
        let shouldReconnect = true;
        const video = videoRef.current;
        if (!streamRef.current) return;
        if (!video || video.readyState < 2) {
          frameTimerRef.current = window.setTimeout(sendNextFrame, 250);
          return;
        }
        if (sendingFrameRef.current) {
          frameTimerRef.current = window.setTimeout(sendNextFrame, 500);
          return;
        }
        sendingFrameRef.current = true;
        try {
          if (!sessionStartedRef.current) {
            const resumeResponse = await fetch(`${API_BASE_URL}/monitoring/my-camera-session`, {
              method: 'POST', headers: { Authorization: `Bearer ${token ?? ''}` },
            });
            if (!resumeResponse.ok) {
              const payload = await resumeResponse.json().catch(() => ({}));
              const sameSession = resumeResponse.status === 409 && typeof payload.detail === 'string' && payload.detail.includes('already active for this driver account');
              if (!sameSession) throw new Error(typeof payload.detail === 'string' ? payload.detail : `Could not reconnect (${resumeResponse.status}).`);
            }
            sessionStartedRef.current = true;
            const sessionConfig = await resumeResponse.json().catch(() => ({}));
            frameConfigRef.current = {
              width: sessionConfig.frameWidth ?? 320,
              height: sessionConfig.frameHeight ?? 240,
              jpegQuality: sessionConfig.jpegQuality ?? 0.55,
              intervalMs: sessionConfig.frameIntervalMs ?? 500,
            };
          }

          const canvas = document.createElement('canvas');
          canvas.width = frameConfigRef.current.width;
          canvas.height = frameConfigRef.current.height;
          const context = canvas.getContext('2d');
          if (!context) return;
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          const frame = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', frameConfigRef.current.jpegQuality));
          if (!frame) return;
          const response = await fetch(`${API_BASE_URL}/monitoring/my-camera-frame`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token ?? ''}`, 'Content-Type': 'image/jpeg' },
            body: frame,
          });
          if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            if (response.status === 409) {
              sessionStartedRef.current = false;
              if (typeof payload.detail === 'string' && payload.detail.includes('restart your camera session')) {
                await fetch(`${API_BASE_URL}/monitoring/my-camera-session`, {
                  method: 'DELETE', headers: { Authorization: `Bearer ${token ?? ''}` },
                });
              }
            }
            if (response.status < 500 && response.status !== 409) shouldReconnect = false;
            throw new Error(typeof payload.detail === 'string' ? payload.detail : `AI frame rejected (${response.status}).`);
          }
          const result = await response.json() as {
            accepted?: boolean;
            status?: DriverMonitoringStatus;
            events?: MonitoringEvent[];
            incidents?: { id: string; driverId: string }[];
          };
          if (result.accepted && result.status) {
            setFramesAccepted((count) => count + 1);
            setLastFrameAt(result.status.frameTimestamp ?? result.status.lastUpdated);
            setPhoneDiagnostics(result.status.phoneDiagnostics);
            setFrameMetrics(result.status);
            setBackendResponse('Frame accepted and analyzed.');
            onMonitoringUpdate?.(result.status);
          } else {
            setBackendResponse('Backend is processing a previous frame; this frame was not queued.');
          }
          if (result.accepted && result.events?.length) onSafetyEvents?.(result.events);
          result.incidents?.forEach((incident) => recorder.triggerIncidentRecording(incident.id, incident.driverId));
          reconnectAttemptsRef.current = 0;
          setError(null);
          setState('live');
        } catch (cause) {
          setError(cause instanceof Error ? cause.message : 'AI monitoring connection was interrupted.');
          reconnectAttemptsRef.current += 1;
          if (shouldReconnect) {
            sessionStartedRef.current = false;
            setState('reconnecting');
            onMonitoringUpdate?.(noSignalStatus(driverId, 'reconnecting'));
          } else {
            sessionStartedRef.current = false;
            fetch(`${API_BASE_URL}/monitoring/my-camera-session`, {
              method: 'DELETE', headers: { Authorization: `Bearer ${token ?? ''}` },
            }).catch(() => {});
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
            if (videoRef.current) videoRef.current.srcObject = null;
            setMediaStream(null);
            setState('error');
            onMonitoringUpdate?.(noSignalStatus(driverId));
          }
        } finally {
          sendingFrameRef.current = false;
          if (shouldReconnect && streamRef.current) {
            const delay = reconnectAttemptsRef.current
              ? Math.min(8000, frameConfigRef.current.intervalMs * (2 ** Math.min(reconnectAttemptsRef.current, 4)))
              : frameConfigRef.current.intervalMs;
            frameTimerRef.current = window.setTimeout(sendNextFrame, delay);
          }
        }
      };
      frameTimerRef.current = window.setTimeout(sendNextFrame, 0);
    } catch (cause) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      setMediaStream(null);
      if (sessionStartedRef.current) {
        sessionStartedRef.current = false;
        fetch(`${API_BASE_URL}/monitoring/my-camera-session`, { method: 'DELETE', headers: { Authorization: `Bearer ${getStoredToken() ?? ''}` } }).catch(() => {});
      }
      setState('error');
      setError(cause instanceof DOMException && cause.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow camera access in your browser settings and try again.'
        : cause instanceof Error ? cause.message : 'Unable to start the camera.');
      setBackendResponse(cause instanceof Error ? cause.message : 'Camera startup failed.');
      onMonitoringUpdate?.(noSignalStatus(driverId));
    }
  };

  useEffect(() => () => {
    if (frameTimerRef.current !== null) window.clearTimeout(frameTimerRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (sessionStartedRef.current) fetch(`${API_BASE_URL}/monitoring/my-camera-session`, { method: 'DELETE', headers: { Authorization: `Bearer ${getStoredToken() ?? ''}` } }).catch(() => {});
  }, []);

  return (
    <Card className="overflow-hidden" padded={false}>
      <div className="p-5 pb-0"><CardHeader title="In-cab camera" subtitle="Live AI safety monitoring for your assigned vehicle" action={
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs ${state === 'live' ? 'bg-status-success-bg text-status-success-text' : 'bg-surface-inset text-text-muted'}`}>
          <Circle size={8} fill="currentColor" />{state === 'live' ? 'AI live' : state === 'reconnecting' ? 'Reconnecting' : state === 'starting' ? 'Starting' : 'Camera off'}
        </span>
      } /></div>
      <div className="relative aspect-video bg-slate-950">
        <video ref={videoRef} className={`h-full w-full object-cover ${state === 'live' || state === 'reconnecting' ? '' : 'hidden'}`} autoPlay muted playsInline />
        {state !== 'live' && state !== 'reconnecting' && <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-300">
          <CameraOff size={34} />
          <span className="text-sm">{state === 'starting' ? 'Requesting camera access…' : 'Camera preview is off'}</span>
        </div>}
        {(state === 'live' || state === 'reconnecting') && <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded bg-black/60 px-2 py-1 text-xs text-white"><Circle size={7} className={state === 'live' ? 'text-red-400' : 'text-amber-400'} fill="currentColor" /> {state === 'live' ? 'AI LIVE' : 'RECONNECTING'}</div>}
      </div>
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-xs text-text-muted">
          <p>When you start monitoring, allow camera access in the browser prompt. Localhost is a trusted camera origin.</p>
          <p className="flex items-center gap-2"><ShieldCheck size={15} />Frames go to the authenticated backend; continuous video is not stored.</p>
          <p className="mt-1">Qualifying incidents save a 5-second pre-event and 10-second post-event clip for fleet review.</p>
        </div>
        <button type="button" onClick={state === 'live' || state === 'reconnecting' ? stopCamera : startCamera} disabled={state === 'starting'} className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-blue px-3 py-2 text-sm font-medium text-white disabled:opacity-60">
          <Camera size={15} />{state === 'live' || state === 'reconnecting' ? 'Stop camera' : state === 'starting' ? 'Starting…' : 'Start AI monitoring'}
        </button>
      </div>
      {import.meta.env.DEV && <div className="border-t border-border px-4 py-3 text-xs text-text-muted" aria-live="polite">
        <p className="font-medium text-text-secondary">Development diagnostics</p>
        <p className="mt-1">Session: {state} · Frames accepted: {framesAccepted} · Last frame: {lastFrameAt ? new Date(lastFrameAt).toLocaleTimeString() : '—'}</p>
        <p className="mt-1">Backend accepted FPS: {frameMetrics.inferenceFps ?? '—'} · MediaPipe: {frameMetrics.mediaPipeLatencyMs ?? '—'} ms · YOLO: {frameMetrics.yoloLatencyMs ?? '—'} ms · total: {frameMetrics.processingLatencyMs ?? '—'} ms (avg {frameMetrics.averageProcessingLatencyMs ?? '—'}, peak {frameMetrics.peakProcessingLatencyMs ?? '—'}) · rejected frames: {frameMetrics.framesRejected ?? 0}</p>
        <p className="mt-1 break-words">Backend: {backendResponse}</p>
        {phoneDiagnostics && <div className="mt-2 space-y-1 break-words">
          <p>YOLO: {phoneDiagnostics.available ? 'active' : 'inactive'} · {phoneDiagnostics.model ?? 'model unknown'} · Ultralytics {phoneDiagnostics.ultralyticsVersion ?? 'unknown'} · class {phoneDiagnostics.modelClassId ?? '—'} {phoneDiagnostics.modelClassName ?? ''}</p>
          <p>Attempted: {phoneDiagnostics.inferenceAttempted ? 'yes' : 'no'} · detections: {phoneDiagnostics.detectionCount ?? 0} · confidence: {phoneDiagnostics.confidence ?? '—'} · bbox: {phoneDiagnostics.bbox?.join(', ') ?? '—'}</p>
          <p>Driver zone: {phoneDiagnostics.driverZone === null || phoneDiagnostics.driverZone === undefined ? '—' : phoneDiagnostics.driverZone ? 'yes' : 'no'} · accepted: {phoneDiagnostics.phoneAccepted ? 'yes' : 'no'} · rejection: {phoneDiagnostics.rejectionReason ?? '—'}</p>
          <p>Frame: {phoneDiagnostics.frameWidth ?? '—'} × {phoneDiagnostics.frameHeight ?? '—'} · YOLO input: {phoneDiagnostics.inputSize ?? '—'} px · confidence threshold: {phoneDiagnostics.confidenceThreshold ?? '—'} · IoU: {phoneDiagnostics.iouThreshold ?? 'Ultralytics default'} · inference: {phoneDiagnostics.lastInferenceMs ?? '—'} ms · average: {phoneDiagnostics.avgInferenceMs ?? '—'} ms · attempts: {phoneDiagnostics.inferenceCount ?? 0}</p>
          {phoneDiagnostics.modelPath && <p>Model path: {phoneDiagnostics.modelPath}</p>}
          {phoneDiagnostics.lastError && <p className="text-status-danger-text">YOLO error: {phoneDiagnostics.lastError}</p>}
        </div>}
      </div>}
      {recorder.recorderState === 'recording_incident' && <p role="status" className="px-4 pb-3 text-xs font-medium text-status-danger-text">Incident clip recording · {recorder.recordingSecondsLeft}s remaining</p>}
      {recorder.recorderState === 'uploading' && <p role="status" className="px-4 pb-3 text-xs text-text-muted">Uploading incident evidence…</p>}
      {recorder.recorderState === 'error' && <p role="status" className="px-4 pb-3 text-xs text-status-danger-text">This browser could not start incident clip recording. Live AI monitoring remains active.</p>}
      {error && <p role="alert" className="px-4 pb-4 text-sm text-status-danger-text">{error}</p>}
    </Card>
  );
}
