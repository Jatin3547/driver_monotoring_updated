export const APP_NAME = 'FleetGuard';

export const MONITORING_EVENT_LABELS: Record<string, string> = {
  drowsiness: 'Drowsiness',
  eye_closure: 'Eye closure',
  yawning: 'Yawning',
  phone_use: 'Phone use',
  distraction: 'Distraction',
  no_presence: 'No presence',
  speeding: 'Speeding',
  'harsh-braking': 'Harsh braking',
  'harsh-acceleration': 'Harsh acceleration',
  'maintenance-due': 'Maintenance due',
  offline: 'Offline',
};

export const VEHICLE_TYPE_LABELS: Record<string, string> = {
  truck: 'Truck',
  van: 'Van',
  car: 'Car',
  bus: 'Bus',
};

export const BENGALURU_CENTER: [number, number] = [12.9716, 77.5946];
