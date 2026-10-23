import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { driverStatusTone } from '@/utils/statusColors';
import { formatDate, formatNumber } from '@/utils/formatDate';
import type { Driver, Vehicle } from '@/types';
import { Phone, Mail, Calendar, Truck } from 'lucide-react';

export function DriverProfilePanel({ driver, vehicle }: { driver: Driver; vehicle?: Vehicle }) {
  return (
    <Card>
      <div className="flex items-start gap-4">
        <span className="w-14 h-14 rounded-full bg-status-info-bg text-status-info-text flex items-center justify-center text-lg font-semibold shrink-0">
          {driver.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
        </span>
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-text-primary">{driver.name}</h2>
          <p className="text-xs text-text-muted mb-2">{driver.id} · {driver.licenseNumber}</p>
          <Badge label={driver.status.replace('-', ' ')} tone={driverStatusTone(driver.status)} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-5 pt-5 border-t border-border text-sm">
        <div className="flex items-center gap-2 text-text-secondary">
          <Phone size={14} className="text-text-muted" /> {driver.phone}
        </div>
        <div className="flex items-center gap-2 text-text-secondary min-w-0">
          <Mail size={14} className="text-text-muted shrink-0" /> <span className="truncate">{driver.email}</span>
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Calendar size={14} className="text-text-muted" /> Joined {formatDate(driver.joinedDate)}
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Truck size={14} className="text-text-muted" /> {vehicle ? vehicle.plateNumber : 'Unassigned'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-5 pt-5 border-t border-border text-center">
        <div>
          <p className="text-xl font-semibold text-text-primary">{driver.safetyScore}</p>
          <p className="text-xs text-text-muted mt-0.5">Safety score</p>
        </div>
        <div>
          <p className="text-xl font-semibold text-text-primary">{formatNumber(driver.totalTrips)}</p>
          <p className="text-xs text-text-muted mt-0.5">Trips</p>
        </div>
        <div>
          <p className="text-xl font-semibold text-text-primary">{formatNumber(driver.totalDistanceKm)}</p>
          <p className="text-xs text-text-muted mt-0.5">km driven</p>
        </div>
      </div>
    </Card>
  );
}
