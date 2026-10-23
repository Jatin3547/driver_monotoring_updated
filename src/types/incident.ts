import type { Severity } from './common';
import type { MonitoringEventType } from './monitoring';

export type IncidentType = MonitoringEventType | 'speeding' | 'harsh-braking' | 'harsh-acceleration';
export type IncidentStatus = 'open' | 'reviewed' | 'resolved';

export interface Incident {
  id: string;
  driverId: string;
  vehicleId?: string;
  tripId?: string;
  evidenceId?: string;
  type: IncidentType;
  severity: Severity;
  status: IncidentStatus;
  timestamp: string; // ISO datetime
  location: string;
  description: string;
  snapshotUrl?: string;
}

export type AlertType = IncidentType | 'maintenance-due' | 'offline';

export interface Alert {
  id: string;
  type: AlertType;
  severity: Severity;
  driverId?: string;
  vehicleId?: string;
  message: string;
  timestamp: string; // ISO datetime
  read: boolean;
}
