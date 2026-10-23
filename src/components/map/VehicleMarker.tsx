import L from 'leaflet';
import type { VehicleStatus } from '@/types';

const statusHex: Record<VehicleStatus, string> = {
  active: '#16A34A',
  idle: '#2563EB',
  maintenance: '#D97706',
  offline: '#DC2626',
};

export function vehicleDivIcon(status: VehicleStatus, heading: number = 0): L.DivIcon {
  const color = statusHex[status];
  return L.divIcon({
    className: '',
    html: `
      <div style="
        width: 28px; height: 28px;
        display: flex; align-items: center; justify-content: center;
        background: ${color};
        border: 2px solid white;
        border-radius: 999px;
        box-shadow: 0 2px 6px rgba(15,23,42,0.35);
        transform: rotate(${heading}deg);
      ">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2 L19 21 L12 17 L5 21 Z" />
        </svg>
      </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}
