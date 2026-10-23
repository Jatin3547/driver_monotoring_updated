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
  confidence: number; // 0-1, populated by AI model in Phase 3
  snapshotUrl?: string;
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
  lastUpdated: string; // ISO datetime
  source?: string;
  cameraStatus?: string;
  aiHealth?: string;
  metrics?: {
    ear?: number;
    mar?: number;
    headYaw?: number;
  };
}
