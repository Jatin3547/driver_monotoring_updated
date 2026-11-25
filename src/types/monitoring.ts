import type { Severity } from './common';

export type MonitoringEventType =
  | 'drowsiness'
  | 'eye_closure'
  | 'yawning'
  | 'phone_use'
  | 'distraction'
  | 'no_presence';

export interface MonitoringEvent {
  id: string;
  driverId: string;
  vehicleId: string;
  type: MonitoringEventType;
  severity: Severity;
  timestamp: string; // ISO datetime
  confidence: number | null; // Present only when supplied by a detector such as YOLO.
  durationSeconds?: number | null;
  metrics?: Record<string, number> | null;
  recoveryState?: 'detected' | 'recovered' | null;
  snapshotUrl?: string;
  source?: 'live' | 'simulation' | string;
}

export type MonitoringSignalStatus = 'normal' | 'warning' | 'critical' | 'no-signal';

export interface DriverMonitoringStatus {
  driverId: string;
  vehicleId: string;
  isOnline: boolean;
  presenceDetected: boolean;
  eyeState: MonitoringSignalStatus;
  drowsinessLevel: MonitoringSignalStatus;
  yawnStatus: MonitoringSignalStatus;
  phoneUseStatus: MonitoringSignalStatus;
  distractionStatus: MonitoringSignalStatus;
  lastUpdated: string;
  source?: 'simulation' | 'live' | 'browser_live' | 'none';
  metrics?: {
    ear: number;
    mar: number;
    headYaw: number;
  };
  processingLatencyMs?: number;
  averageProcessingLatencyMs?: number;
  peakProcessingLatencyMs?: number;
  framesRejected?: number;
  mediaPipeLatencyMs?: number;
  yoloLatencyMs?: number | null;
  inferenceFps?: number;
  frameTimestamp?: string;
  cameraStatus?: 'active' | 'browser_active' | 'disconnected' | 'reconnecting' | 'simulated' | 'stopped' | string;
  aiHealth?: 'healthy' | 'degraded';
  error?: string | null;
  phoneDiagnostics?: {
    available?: boolean;
    model?: string;
    modelPath?: string | null;
    ultralyticsVersion?: string | null;
    modelClassId?: number;
    modelClassName?: string | null;
    classesFiltered?: number[];
    confidenceThreshold?: number;
    inputSize?: number;
    iouThreshold?: number | null;
    inferenceCount?: number;
    avgInferenceMs?: number;
    lastError?: string | null;
    inferenceAttempted?: boolean;
    detectionCount?: number;
    detectedClassId?: number | null;
    confidence?: number | null;
    bbox?: number[] | null;
    driverZone?: boolean | null;
    phoneAccepted?: boolean;
    rejectionReason?: string | null;
    lastInferenceMs?: number | null;
    frameWidth?: number | null;
    frameHeight?: number | null;
  };
}
