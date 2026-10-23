import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { vehicleDivIcon } from './VehicleMarker';
import { BENGALURU_CENTER } from '@/utils/constants';
import { Badge } from '@/components/ui/Badge';
import { vehicleStatusTone } from '@/utils/statusColors';
import type { Driver, Vehicle, VehicleLocation } from '@/types';

interface Props {
  locations: VehicleLocation[];
  vehicles: Vehicle[];
  drivers: Driver[];
  height?: string;
}

export function FleetMap({ locations, vehicles, drivers, height = '420px' }: Props) {
  const vehicleById = new Map(vehicles.map((v) => [v.id, v]));
  const driverById = new Map(drivers.map((d) => [d.id, d]));

  return (
    <div style={{ height }} className="rounded-lg overflow-hidden border border-border">
      <MapContainer
        center={BENGALURU_CENTER}
        zoom={12}
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {locations.map((loc) => {
          const vehicle = vehicleById.get(loc.vehicleId);
          if (!vehicle) return null;
          const driver = vehicle.assignedDriverId ? driverById.get(vehicle.assignedDriverId) : undefined;
          return (
            <Marker
              key={loc.vehicleId}
              position={[loc.lat, loc.lng]}
              icon={vehicleDivIcon(vehicle.status, loc.heading)}
            >
              <Popup>
                <div className="text-xs space-y-1.5 min-w-[160px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-sm">{vehicle.plateNumber}</span>
                    <Badge label={vehicle.status} tone={vehicleStatusTone(vehicle.status)} />
                  </div>
                  <p className="text-slate-600">{vehicle.make} {vehicle.model}</p>
                  {driver && <p className="text-slate-600">Driver: {driver.name}</p>}
                  <p className="text-slate-600">Speed: {loc.speedKmh} km/h</p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
