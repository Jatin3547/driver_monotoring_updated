import { DriverMonitorCard } from './DriverMonitorCard';
import { EmptyState } from '@/components/ui/States';
import { ScanEye } from 'lucide-react';
import type { Driver, DriverMonitoringStatus, Vehicle } from '@/types';

interface Props {
  statuses: DriverMonitoringStatus[];
  drivers: Driver[];
  vehicles: Vehicle[];
}

export function MonitoringStatusGrid({ statuses, drivers, vehicles }: Props) {
  if (statuses.length === 0) {
    return <EmptyState icon={ScanEye} title="No active monitoring sessions" description="Monitoring feeds will appear here once the AI service is connected in Phase 3." />;
  }

  const driverById = new Map(drivers.map((d) => [d.id, d]));
  const vehicleById = new Map(vehicles.map((v) => [v.id, v]));

  // Ensure the live monitored person (DRV-001 or live source) is always at the top position
  const sortedStatuses = [...statuses].sort((a, b) => {
    const aLive = a.driverId === 'DRV-001' || a.source === 'live';
    const bLive = b.driverId === 'DRV-001' || b.source === 'live';
    if (aLive && !bLive) return -1;
    if (!aLive && bLive) return 1;
    return a.driverId.localeCompare(b.driverId);
  });

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {sortedStatuses.map((status) => (
        <DriverMonitorCard
          key={status.driverId}
          status={status}
          driver={driverById.get(status.driverId)}
          vehicle={vehicleById.get(status.vehicleId)}
        />
      ))}
    </div>
  );
}
