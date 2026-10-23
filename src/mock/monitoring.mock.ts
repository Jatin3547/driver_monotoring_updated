import type { DriverMonitoringStatus, MonitoringEvent } from '@/types';

export const mockMonitoringStatuses: DriverMonitoringStatus[] = [
  { driverId: 'DRV-001', vehicleId: 'VEH-001', isOnline: true, presenceDetected: true, eyeState: 'normal', drowsinessLevel: 'normal', yawnStatus: 'normal', phoneUseStatus: 'normal', distractionStatus: 'normal', lastUpdated: '2026-09-25T09:12:04Z' },
  { driverId: 'DRV-002', vehicleId: 'VEH-002', isOnline: true, presenceDetected: true, eyeState: 'warning', drowsinessLevel: 'warning', yawnStatus: 'normal', phoneUseStatus: 'normal', distractionStatus: 'normal', lastUpdated: '2026-09-25T09:11:50Z' },
  { driverId: 'DRV-003', vehicleId: 'VEH-003', isOnline: true, presenceDetected: true, eyeState: 'normal', drowsinessLevel: 'normal', yawnStatus: 'normal', phoneUseStatus: 'normal', distractionStatus: 'normal', lastUpdated: '2026-09-25T09:12:01Z' },
  { driverId: 'DRV-005', vehicleId: 'VEH-005', isOnline: true, presenceDetected: true, eyeState: 'critical', drowsinessLevel: 'critical', yawnStatus: 'warning', phoneUseStatus: 'normal', distractionStatus: 'warning', lastUpdated: '2026-09-25T09:12:06Z' },
  { driverId: 'DRV-006', vehicleId: 'VEH-006', isOnline: true, presenceDetected: true, eyeState: 'normal', drowsinessLevel: 'normal', yawnStatus: 'normal', phoneUseStatus: 'warning', distractionStatus: 'normal', lastUpdated: '2026-09-25T09:11:47Z' },
  { driverId: 'DRV-008', vehicleId: 'VEH-007', isOnline: true, presenceDetected: true, eyeState: 'normal', drowsinessLevel: 'normal', yawnStatus: 'normal', phoneUseStatus: 'normal', distractionStatus: 'normal', lastUpdated: '2026-09-25T09:12:02Z' },
  { driverId: 'DRV-009', vehicleId: 'VEH-008', isOnline: false, presenceDetected: false, eyeState: 'no-signal', drowsinessLevel: 'no-signal', yawnStatus: 'no-signal', phoneUseStatus: 'no-signal', distractionStatus: 'no-signal', lastUpdated: '2026-09-25T08:40:12Z' },
];

export const mockMonitoringEvents: MonitoringEvent[] = [
  { id: 'EVT-1001', driverId: 'DRV-005', vehicleId: 'VEH-005', type: 'drowsiness', severity: 'high', timestamp: '2026-09-25T09:11:40Z', confidence: 0.91 },
  { id: 'EVT-1002', driverId: 'DRV-005', vehicleId: 'VEH-005', type: 'eye_closure', severity: 'high', timestamp: '2026-09-25T09:11:55Z', confidence: 0.88 },
  { id: 'EVT-1003', driverId: 'DRV-002', vehicleId: 'VEH-002', type: 'yawning', severity: 'medium', timestamp: '2026-09-25T09:05:12Z', confidence: 0.74 },
  { id: 'EVT-1004', driverId: 'DRV-006', vehicleId: 'VEH-006', type: 'phone_use', severity: 'medium', timestamp: '2026-09-25T08:58:30Z', confidence: 0.81 },
  { id: 'EVT-1005', driverId: 'DRV-009', vehicleId: 'VEH-008', type: 'no_presence', severity: 'high', timestamp: '2026-09-25T08:40:05Z', confidence: 0.95 },
  { id: 'EVT-1006', driverId: 'DRV-003', vehicleId: 'VEH-003', type: 'distraction', severity: 'low', timestamp: '2026-09-25T08:22:19Z', confidence: 0.62 },
  { id: 'EVT-1007', driverId: 'DRV-001', vehicleId: 'VEH-001', type: 'yawning', severity: 'low', timestamp: '2026-09-25T07:59:44Z', confidence: 0.58 },
  { id: 'EVT-1008', driverId: 'DRV-002', vehicleId: 'VEH-002', type: 'drowsiness', severity: 'medium', timestamp: '2026-09-25T07:41:03Z', confidence: 0.7 },
];
