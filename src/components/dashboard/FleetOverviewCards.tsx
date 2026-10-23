import { Truck, Users, AlertTriangle, ShieldCheck } from 'lucide-react';
import { StatCard } from '@/components/ui/StatCard';
import type { Driver } from '@/types';
import type { Vehicle } from '@/types';
import type { Incident } from '@/types';

interface Props {
  drivers: Driver[];
  vehicles: Vehicle[];
  incidents: Incident[];
}

export function FleetOverviewCards({ drivers, vehicles, incidents }: Props) {
  const activeVehicles = vehicles.filter((v) => v.status === 'active').length;
  const driversOnTrip = drivers.filter((d) => d.status === 'on-trip').length;
  const openIncidents = incidents.filter((i) => i.status === 'open').length;
  const avgSafetyScore = Math.round(
    drivers.reduce((sum, d) => sum + d.safetyScore, 0) / (drivers.length || 1),
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard
        label="Active vehicles"
        value={`${activeVehicles} / ${vehicles.length}`}
        icon={Truck}
        iconTone="blue"
        trend={{ value: `${vehicles.length - activeVehicles} idle/down`, direction: 'down', positive: false }}
      />
      <StatCard
        label="Drivers on trip"
        value={`${driversOnTrip} / ${drivers.length}`}
        icon={Users}
        iconTone="green"
      />
      <StatCard
        label="Open incidents"
        value={String(openIncidents)}
        icon={AlertTriangle}
        iconTone="red"
        trend={{ value: 'Needs review', direction: 'up', positive: false }}
      />
      <StatCard
        label="Avg. safety score"
        value={`${avgSafetyScore}`}
        icon={ShieldCheck}
        iconTone="amber"
      />
    </div>
  );
}
