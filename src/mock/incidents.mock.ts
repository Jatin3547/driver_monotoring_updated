import type { Alert, Incident } from '@/types';

export const mockIncidents: Incident[] = [
  { id: 'INC-501', driverId: 'DRV-005', vehicleId: 'VEH-005', type: 'drowsiness', severity: 'high', status: 'open', timestamp: '2026-09-25T09:11:40Z', location: 'Outer Ring Road, Bengaluru', description: 'Sustained eye closure detected for 2.4 seconds at 78 km/h.' },
  { id: 'INC-502', driverId: 'DRV-005', vehicleId: 'VEH-005', type: 'harsh-braking', severity: 'medium', status: 'open', timestamp: '2026-09-25T08:55:12Z', location: 'Hebbal Flyover, Bengaluru', description: 'Deceleration of -6.2 m/s\u00b2 recorded, exceeding safe threshold.' },
  { id: 'INC-503', driverId: 'DRV-007', vehicleId: undefined, type: 'phone_use', severity: 'high', status: 'reviewed', timestamp: '2026-09-24T17:20:00Z', location: 'MG Road, Bengaluru', description: 'Repeated handheld phone use while vehicle in motion.' },
  { id: 'INC-504', driverId: 'DRV-002', vehicleId: 'VEH-002', type: 'yawning', severity: 'medium', status: 'reviewed', timestamp: '2026-09-24T14:02:33Z', location: 'Whitefield, Bengaluru', description: 'Frequent yawning pattern flagged over a 10-minute window.' },
  { id: 'INC-505', driverId: 'DRV-009', vehicleId: 'VEH-008', type: 'no_presence', severity: 'high', status: 'open', timestamp: '2026-09-25T08:40:05Z', location: 'Yeshwanthpur, Bengaluru', description: 'Driver not detected in frame while ignition was on.' },
  { id: 'INC-506', driverId: 'DRV-003', vehicleId: 'VEH-003', type: 'speeding', severity: 'low', status: 'resolved', timestamp: '2026-09-23T11:15:40Z', location: 'NH44, Bengaluru', description: 'Speed of 96 km/h recorded in an 80 km/h zone for 40 seconds.' },
  { id: 'INC-507', driverId: 'DRV-001', vehicleId: 'VEH-001', type: 'distraction', severity: 'low', status: 'resolved', timestamp: '2026-09-22T09:30:10Z', location: 'Electronic City, Bengaluru', description: 'Head-pose deviation exceeded threshold for 3 seconds.' },
  { id: 'INC-508', driverId: 'DRV-007', vehicleId: undefined, type: 'harsh-acceleration', severity: 'medium', status: 'resolved', timestamp: '2026-09-21T18:44:22Z', location: 'Silk Board, Bengaluru', description: 'Acceleration of 3.1 m/s\u00b2 recorded from standstill.' },
  { id: 'INC-509', driverId: 'DRV-006', vehicleId: 'VEH-006', type: 'phone_use', severity: 'low', status: 'open', timestamp: '2026-09-25T08:58:30Z', location: 'Malleshwaram, Bengaluru', description: 'Brief handheld phone use detected at a traffic signal.' },
];

export const mockAlerts: Alert[] = [
  { id: 'ALT-9001', type: 'drowsiness', severity: 'high', driverId: 'DRV-005', vehicleId: 'VEH-005', message: 'Critical drowsiness detected — Vikram Singh (VEH-005)', timestamp: '2026-09-25T09:11:40Z', read: false },
  { id: 'ALT-9002', type: 'no_presence', severity: 'high', driverId: 'DRV-009', vehicleId: 'VEH-008', message: 'Driver presence lost — Suresh Kumar (VEH-008)', timestamp: '2026-09-25T08:40:05Z', read: false },
  { id: 'ALT-9003', type: 'harsh-braking', severity: 'medium', driverId: 'DRV-005', vehicleId: 'VEH-005', message: 'Harsh braking event — VEH-005 on Hebbal Flyover', timestamp: '2026-09-25T08:55:12Z', read: false },
  { id: 'ALT-9004', type: 'phone_use', severity: 'medium', driverId: 'DRV-006', vehicleId: 'VEH-006', message: 'Phone use while driving — Anita Desai (VEH-006)', timestamp: '2026-09-25T08:58:30Z', read: true },
  { id: 'ALT-9005', type: 'maintenance-due', severity: 'low', vehicleId: 'VEH-008', message: 'VEH-008 approaching scheduled service interval', timestamp: '2026-09-25T07:15:00Z', read: true },
  { id: 'ALT-9006', type: 'offline', severity: 'low', vehicleId: 'VEH-009', message: 'VEH-009 has gone offline — no signal for 3 hours', timestamp: '2026-09-25T06:20:00Z', read: true },
  { id: 'ALT-9007', type: 'yawning', severity: 'low', driverId: 'DRV-002', vehicleId: 'VEH-002', message: 'Yawning pattern flagged — Priya Nair (VEH-002)', timestamp: '2026-09-25T09:05:12Z', read: false },
];
