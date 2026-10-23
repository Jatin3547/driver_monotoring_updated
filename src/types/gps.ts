export interface VehicleLocation {
  vehicleId: string;
  lat: number;
  lng: number;
  speedKmh: number;
  heading: number; // degrees
  accelerationMs2: number; // signed; negative = braking
  timestamp: string; // ISO datetime
}

export interface RoutePoint {
  lat: number;
  lng: number;
  timestamp: string;
}
