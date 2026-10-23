import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { vehicleStatusTone } from '@/utils/statusColors';
import { formatDate, formatNumber } from '@/utils/formatDate';
import { VEHICLE_TYPE_LABELS } from '@/utils/constants';
import type { Driver, Vehicle } from '@/types';
import { Gauge, Wrench, Fuel, User } from 'lucide-react';

export function VehicleInfoPanel({ vehicle, driver }: { vehicle: Vehicle; driver?: Driver }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">{vehicle.plateNumber}</h2>
          <p className="text-xs text-text-muted mt-0.5">
            {vehicle.make} {vehicle.model} · {vehicle.year} · {VEHICLE_TYPE_LABELS[vehicle.type]}
          </p>
        </div>
        <Badge label={vehicle.status} tone={vehicleStatusTone(vehicle.status)} />
      </div>

      <div className="grid grid-cols-2 gap-4 mt-5 pt-5 border-t border-border text-sm">
        <div className="flex items-center gap-2 text-text-secondary">
          <User size={14} className="text-text-muted" /> {driver ? driver.name : 'Unassigned'}
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Gauge size={14} className="text-text-muted" /> {formatNumber(vehicle.odometerKm)} km
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Fuel size={14} className="text-text-muted" /> {vehicle.fuelLevel}% fuel
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Wrench size={14} className="text-text-muted" /> Serviced {formatDate(vehicle.lastServiceDate)}
        </div>
      </div>

      <div className="mt-5 pt-5 border-t border-border">
        <div className="flex items-center justify-between text-xs text-text-muted mb-1.5">
          <span>Odometer</span>
          <span>Next service at {formatNumber(vehicle.nextServiceDueKm)} km</span>
        </div>
        <div className="h-1.5 rounded-full bg-surface-inset overflow-hidden">
          <div
            className="h-full bg-brand-blue"
            style={{
              width: `${Math.min(100, (vehicle.odometerKm / vehicle.nextServiceDueKm) * 100)}%`,
            }}
          />
        </div>
      </div>
    </Card>
  );
}
