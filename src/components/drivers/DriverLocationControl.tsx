import { useEffect, useRef, useState } from 'react';
import { MapPin, MapPinOff } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { updateMyGPSLocation } from '@/services/api/gpsService';
import type { DriverGPSConfig, DriverGPSUpdate, VehicleLocation } from '@/types';
import { getDriverGPSConfig } from '@/services/api/gpsService';

type LocationState = 'stopped' | 'requesting' | 'active' | 'stale' | 'unavailable' | 'denied';
type BrowserPoint = { lat: number; lng: number; accuracy: number; speed: number | null; heading: number | null; timestamp: number };

const DEFAULT_GPS_CONFIG: DriverGPSConfig = {
  minimumIntervalSeconds: 3,
  updateIntervalSeconds: 5,
  minMovementMeters: 15,
  staleAfterSeconds: 30,
  maxAccuracyMeters: 10000,
};

function distanceMeters(a: BrowserPoint, b: BrowserPoint) {
  const radians = (value: number) => value * Math.PI / 180;
  const dLat = radians(b.lat - a.lat);
  const dLng = radians(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(radians(a.lat)) * Math.cos(radians(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 6_371_000 * 2 * Math.asin(Math.sqrt(h));
}

export function DriverLocationControl({
  driverId,
  vehicleId,
  onLocation,
}: {
  driverId: string;
  vehicleId?: string;
  onLocation?: (location: VehicleLocation) => void;
}) {
  const [state, setState] = useState<LocationState>('stopped');
  const [message, setMessage] = useState('Location permission required. Start sharing when you are ready.');
  const [point, setPoint] = useState<BrowserPoint | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [staleAfterSeconds, setStaleAfterSeconds] = useState(30);
  const gpsConfigRef = useRef(DEFAULT_GPS_CONFIG);
  const [serverMessage, setServerMessage] = useState('');
  const watchIdRef = useRef<number | null>(null);
  const previousSentRef = useRef<BrowserPoint | null>(null);
  const stoppedRef = useRef(true);

  const stop = () => {
    stoppedRef.current = true;
    if (watchIdRef.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchIdRef.current);
    watchIdRef.current = null;
    previousSentRef.current = null;
    setState('stopped');
    setMessage('Location stopped. Your last accepted position remains visible as stale until it expires.');
  };

  const start = () => {
    if (!navigator.geolocation) {
      setState('unavailable');
      setMessage('This browser does not support geolocation.');
      return;
    }
    if (watchIdRef.current !== null) navigator.geolocation.clearWatch(watchIdRef.current);
    stoppedRef.current = false;
    setState('requesting');
    setMessage('Requesting location permission and waiting for a GPS position…');
    watchIdRef.current = navigator.geolocation.watchPosition(async (position) => {
      if (stoppedRef.current) return;
      const coords = position.coords;
      const current: BrowserPoint = {
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracy,
        speed: coords.speed,
        heading: coords.heading,
        timestamp: position.timestamp,
      };
      setPoint(current);
      setState('active');
      setMessage(coords.accuracy > 100 ? 'Live location active; browser accuracy is coarse and is shown as reported.' : 'Live location active.');

      if (coords.accuracy > gpsConfigRef.current.maxAccuracyMeters) {
        setServerMessage(`Reported accuracy ±${Math.round(coords.accuracy)} m exceeds the configured limit; this fix was not uploaded.`);
        return;
      }

      const previous = previousSentRef.current;
      const elapsed = previous ? current.timestamp - previous.timestamp : Infinity;
      if (previous && elapsed < gpsConfigRef.current.minimumIntervalSeconds * 1000) return;
      const accuracyAwareThreshold = Math.max(gpsConfigRef.current.minMovementMeters, current.accuracy, previous?.accuracy ?? 0);
      if (previous && elapsed < gpsConfigRef.current.updateIntervalSeconds * 1000 && distanceMeters(previous, current) < accuracyAwareThreshold) return;

      previousSentRef.current = current;
      const update: DriverGPSUpdate = {
        latitude: current.lat,
        longitude: current.lng,
        accuracy: current.accuracy,
        speed: current.speed,
        heading: current.heading,
        timestamp: new Date(current.timestamp).toISOString(),
      };
      try {
        const result = await updateMyGPSLocation(update);
        if (result.accepted && result.location) {
          setState('active');
          setLastUpdate(result.location.timestamp);
          setStaleAfterSeconds(result.location.staleAfterSeconds);
          setServerMessage('Location sent securely for your assigned vehicle.');
          onLocation?.(result.location);
        } else {
          setServerMessage(`Update held by rate/movement limit${result.retryAfterSeconds ? `; retry in about ${result.retryAfterSeconds}s` : ''}.`);
        }
      } catch (error) {
        setServerMessage(error instanceof Error ? error.message : 'Could not send location update.');
      }
    }, (error) => {
      if (stoppedRef.current) return;
      if (error.code === error.PERMISSION_DENIED) {
        if (watchIdRef.current !== null) navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
        setState('denied');
        setMessage('Location permission was denied. Allow it in browser site settings to share live GPS.');
      } else {
        setState('unavailable');
        setMessage(error.code === error.TIMEOUT ? 'GPS timed out. Checking again for a usable position…' : 'GPS signal is unavailable. The camera monitor can continue independently.');
      }
    }, { enableHighAccuracy: true, maximumAge: 3000, timeout: 15000 });
  };

  useEffect(() => () => {
    stoppedRef.current = true;
    if (watchIdRef.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchIdRef.current);
  }, []);

  useEffect(() => {
    getDriverGPSConfig().then((config) => {
      gpsConfigRef.current = config;
      setStaleAfterSeconds(config.staleAfterSeconds);
    }).catch(() => {
      // The first live update still attempts the authenticated API; local cadence has safe defaults.
    });
  }, []);

  useEffect(() => {
    if (!lastUpdate) return;
    const timer = window.setInterval(() => {
      if (Date.now() - new Date(lastUpdate).getTime() > staleAfterSeconds * 1000) {
        setState((current) => current === 'active' ? 'stale' : current);
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [lastUpdate, staleAfterSeconds]);

  const stateLabel = state === 'active' ? 'LIVE GPS' : state === 'stale' ? 'GPS signal stale' : state === 'denied' ? 'Permission denied' : state === 'unavailable' ? 'GPS unavailable' : state === 'requesting' ? 'Requesting location' : 'Location stopped';
  const stateTone = state === 'active' ? 'text-emerald-600' : state === 'stale' || state === 'denied' || state === 'unavailable' ? 'text-amber-600' : 'text-text-muted';

  return (
    <Card>
      <CardHeader title="Live location sharing" subtitle={vehicleId ? `Assigned vehicle: ${vehicleId}` : 'Assign a vehicle before sharing location'} action={state === 'active' ? <MapPin size={17} className="text-emerald-600" /> : <MapPinOff size={17} className="text-text-muted" />} />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <span className={`text-sm font-semibold ${stateTone}`}>{stateLabel}</span>
        {state === 'active' || state === 'stale' || state === 'requesting' ? (
          <button type="button" onClick={stop} className="rounded-md border border-border px-3 py-2 text-sm font-medium text-text-primary">Stop location</button>
        ) : (
          <button type="button" onClick={start} disabled={!vehicleId} className="rounded-md bg-brand-blue px-3 py-2 text-sm font-medium text-white disabled:opacity-50">Start live location</button>
        )}
      </div>
      <p className="mt-2 text-xs text-text-muted">{message}</p>
      {serverMessage && <p className="mt-1 text-xs text-text-muted">{serverMessage}</p>}
      {import.meta.env.DEV && <p className="mt-2 text-xs text-text-muted">Authenticated driver: {driverId} · vehicle assignment is resolved by the backend.</p>}
      {import.meta.env.DEV && point && <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3 text-xs text-text-muted">
        <span>Latitude: {point.lat.toFixed(6)}</span><span>Longitude: {point.lng.toFixed(6)}</span>
        <span>Accuracy: ±{Math.round(point.accuracy)} m</span><span>Speed: {point.speed === null ? '—' : `${(point.speed * 3.6).toFixed(1)} km/h`}</span>
        <span>Heading: {point.heading === null ? '—' : `${Math.round(point.heading)}°`}</span><span>Last sent: {lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : 'pending'}</span>
      </div>}
      {!import.meta.env.DEV && point && <p className="mt-2 text-xs text-text-muted">Reported accuracy ±{Math.round(point.accuracy)} m · Last sent {lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : 'pending'}</p>}
    </Card>
  );
}
