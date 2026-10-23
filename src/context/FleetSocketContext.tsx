import { createContext, type ReactNode } from 'react';
import { useFleetSocket } from '@/hooks/useFleetSocket';
import type { FleetSocketMessage, WebSocketStatus } from '@/hooks/useFleetSocket';
import { USE_MOCK_DATA } from '@/services/config';

interface FleetSocketContextValue {
  status: WebSocketStatus;
  subscribe: (listener: (message: FleetSocketMessage) => void) => () => void;
}

export const FleetSocketContext = createContext<FleetSocketContextValue | undefined>(undefined);

export function FleetSocketProvider({ children }: { children: ReactNode }) {
  // One connection for the whole app, only opened when not in mock mode —
  // there is no backend socket to connect to in the default demo.
  const { status, subscribe } = useFleetSocket(!USE_MOCK_DATA);

  return (
    <FleetSocketContext.Provider value={{ status, subscribe }}>{children}</FleetSocketContext.Provider>
  );
}
