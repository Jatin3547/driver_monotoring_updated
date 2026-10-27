import { useEffect, useRef, useState, useCallback } from 'react';
import { uploadIncidentEvidence } from '@/services/api/evidenceService';
import { API_BASE_URL } from '@/services/config';
import { getStoredToken } from '@/services/api/authService';

interface UseIncidentRecorderProps {
  stream: MediaStream | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  driverId?: string;
  isLiveFeedValid?: boolean;
  onUploadSuccess?: (incidentId: string) => void;
  onUploadError?: (error: Error) => void;
}

export type RecorderState = 'idle' | 'buffering' | 'recording_incident' | 'uploading' | 'error';

interface BufferedChunk {
  timestamp: number;
  data: Blob;
}

export function useIncidentRecorder({
  stream,
  videoRef,
  driverId = 'DRV-001',
  isLiveFeedValid = true,
  onUploadSuccess,
  onUploadError,
}: UseIncidentRecorderProps) {
  const [recorderState, setRecorderState] = useState<RecorderState>('idle');
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);
  const [recordingSecondsLeft, setRecordingSecondsLeft] = useState<number>(0);
  const [lastUploadedIncidentId, setLastUploadedIncidentId] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const headerChunkRef = useRef<Blob | null>(null);
  const rollingBufferRef = useRef<BufferedChunk[]>([]);
  const postEventChunksRef = useRef<Blob[]>([]);
  const activeIncidentRef = useRef<string | null>(null);
  const activeTriggerTimestampRef = useRef<string | null>(null);
  const snapshotBlobRef = useRef<Blob | null>(null);
  const postEventTimerRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);

  // Progressive MIME type detection for browser support
  const getSupportedMimeType = (): string => {
    if (typeof MediaRecorder === 'undefined') return 'video/webm';
    const candidates = [
      'video/webm;codecs=vp8,opus',
      'video/webm;codecs=vp8',
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp9',
      'video/webm',
    ];
    for (const t of candidates) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return 'video/webm';
  };

  // Capture representative still JPEG frame from active video element or backend snapshot
  const captureStillSnapshot = useCallback((): Promise<Blob | null> => {
    const video = videoRef.current;
    if (video && video.readyState >= 2) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          return new Promise<Blob | null>((resolve) => {
            canvas.toBlob((b) => resolve(b), 'image/jpeg', 0.9);
          });
        }
      } catch {
        // Fall back to backend snapshot endpoint below
      }
    }

    // Direct snapshot fallback from backend
    return fetch(`${API_BASE_URL}/monitoring/current-snapshot`, {
      headers: { Authorization: `Bearer ${getStoredToken() ?? ''}` },
    })
      .then((res) => {
        if (res.ok) return res.blob();
        return null;
      })
      .catch(() => null);
  }, [videoRef]);

  // Start continuous rolling buffer when media stream is live
  useEffect(() => {
    if (!stream || stream.getVideoTracks().length === 0) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      mediaRecorderRef.current = null;
      headerChunkRef.current = null;
      rollingBufferRef.current = [];
      setRecorderState('idle');
      return;
    }

    try {
      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      headerChunkRef.current = null;
      rollingBufferRef.current = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (!event.data || event.data.size === 0) return;

        // The very first chunk produced by MediaRecorder contains the EBML container header
        if (!headerChunkRef.current) {
          headerChunkRef.current = event.data;
        }

        const now = Date.now();
        // If actively recording a triggered incident, collect post-event chunks
        if (activeIncidentRef.current) {
          postEventChunksRef.current.push(event.data);
        }

        // Maintain rolling in-memory buffer of ~5 seconds of footage
        rollingBufferRef.current.push({ timestamp: now, data: event.data });
        const cutoff = now - 5500; // 5.5 seconds window
        rollingBufferRef.current = rollingBufferRef.current.filter((c) => c.timestamp >= cutoff);
      };

      recorder.onerror = () => {
        setRecorderState('error');
      };

      // Request slices every 500ms for fine-grained 5s rolling buffer
      recorder.start(500);
      setRecorderState('buffering');
    } catch (err) {
      console.warn('Failed to start MediaRecorder for evidence rolling buffer:', err);
      setRecorderState('error');
    }

    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // Ignore cleanup errors
        }
      }
      mediaRecorderRef.current = null;
      headerChunkRef.current = null;
      rollingBufferRef.current = [];
      if (postEventTimerRef.current) window.clearTimeout(postEventTimerRef.current);
      if (countdownIntervalRef.current) window.clearInterval(countdownIntervalRef.current);
    };
  }, [stream]);

  // Triggered when a critical event / incident occurs for the active driver
  const triggerIncidentRecording = useCallback(
    async (incidentId: string, eventDriverId?: string) => {
      // Duplicate event suppression: if already recording an incident, ignore duplicate triggers
      if (activeIncidentRef.current) {
        return;
      }

      // Check driver match
      if (eventDriverId && eventDriverId !== driverId && eventDriverId !== 'DRV-001') {
        return;
      }

      // Reject recording if live camera feed is invalid / DroidCam splash screen
      if (!isLiveFeedValid) {
        const warning = 'Evidence recording aborted: Camera stream contains DroidCam splash screen placeholder instead of live driver.';
        console.warn(warning);
        if (onUploadError) onUploadError(new Error(warning));
        return;
      }

      if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
        return;
      }

      activeIncidentRef.current = incidentId;
      setActiveIncidentId(incidentId);
      activeTriggerTimestampRef.current = new Date().toISOString();
      setRecorderState('recording_incident');
      setRecordingSecondsLeft(10);

      // 1. Snapshot representative still JPEG at the exact trigger moment
      try {
        const snap = await captureStillSnapshot();
        snapshotBlobRef.current = snap;
      } catch {
        snapshotBlobRef.current = null;
      }

      // 2. Snapshot the last 5.0 seconds from rolling buffer
      const preEventBlobs = rollingBufferRef.current.map((c) => c.data);
      postEventChunksRef.current = [];

      // Start 10-second countdown ticker for UI
      let secondsRemaining = 10;
      if (countdownIntervalRef.current) window.clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = window.setInterval(() => {
        secondsRemaining -= 1;
        setRecordingSecondsLeft(Math.max(0, secondsRemaining));
        if (secondsRemaining <= 0 && countdownIntervalRef.current) {
          window.clearInterval(countdownIntervalRef.current);
          countdownIntervalRef.current = null;
        }
      }, 1000);

      // 3. Continue recording for 10.0 seconds post-trigger
      if (postEventTimerRef.current) window.clearTimeout(postEventTimerRef.current);
      postEventTimerRef.current = window.setTimeout(async () => {
        setRecorderState('uploading');

        // Concatenate pre-event chunks (~5s) + post-event chunks (10s)
        const mimeType = mediaRecorderRef.current?.mimeType || 'video/webm';
        const finalChunks: Blob[] = [];

        // Include EBML container header chunk if available and not already in preEvent
        if (headerChunkRef.current && !preEventBlobs.includes(headerChunkRef.current)) {
          finalChunks.push(headerChunkRef.current);
        }
        finalChunks.push(...preEventBlobs, ...postEventChunksRef.current);

        const videoBlob = new Blob(finalChunks, { type: mimeType });
        const snapshotBlob = snapshotBlobRef.current || undefined;
        const triggerTs = activeTriggerTimestampRef.current || new Date().toISOString();

        try {
          await uploadIncidentEvidence(
            incidentId,
            videoBlob,
            snapshotBlob,
            5.0,
            10.0,
            triggerTs
          );
          setLastUploadedIncidentId(incidentId);
          if (onUploadSuccess) onUploadSuccess(incidentId);
        } catch (err: unknown) {
          const error = err instanceof Error ? err : new Error(String(err));
          console.error('Failed to upload incident video evidence:', error);
          if (onUploadError) onUploadError(error);
        } finally {
          activeIncidentRef.current = null;
          setActiveIncidentId(null);
          postEventChunksRef.current = [];
          snapshotBlobRef.current = null;
          setRecorderState('buffering');
          setRecordingSecondsLeft(0);
        }
      }, 10000);
    },
    [driverId, isLiveFeedValid, captureStillSnapshot, onUploadSuccess, onUploadError]
  );

  return {
    recorderState,
    activeIncidentId,
    recordingSecondsLeft,
    lastUploadedIncidentId,
    triggerIncidentRecording,
  };
}
