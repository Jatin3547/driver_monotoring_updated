export interface VehicleLocation {
  vehicleId: string;
  driverId?: string | null;
  lat: number;
  lng: number;
  speedKmh: number | null;
  heading: number | null; // degrees
  accelerationMs2: number; // signed; negative = braking
  accuracyM?: number | null;
  source: 'live' | 'simulation' | string;
  gpsStatus: 'live' | 'simulated' | 'stale' | string;
  staleAfterSeconds: number;
  timestamp: string; // ISO datetime
}

export interface DriverGPSUpdate {
  latitude: number;
  longitude: number;
  accuracy: number;
  speed: number | null; // browser Geolocation API uses m/s
  heading: number | null;
  timestamp: string;
}

export interface DriverGPSUpdateResult {
  accepted: boolean;
  reason?: string;
  retryAfterSeconds?: number;
  location?: VehicleLocation;
}

export interface DriverGPSConfig {
  updateIntervalSeconds: number;
  minimumIntervalSeconds: number;
  minMovementMeters: number;
  staleAfterSeconds: number;
  maxAccuracyMeters: number;
}

export interface RoutePoint {
  lat: number;
  lng: number;
  timestamp: string;
}
