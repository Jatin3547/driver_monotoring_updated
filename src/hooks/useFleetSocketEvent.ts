import { useContext, useEffect } from 'react';
import { FleetSocketContext } from '@/context/FleetSocketContext';
import type { FleetSocketMessage } from '@/hooks/useFleetSocket';

export function useFleetSocketContext() {
  const ctx = useContext(FleetSocketContext);
  if (!ctx) throw new Error('useFleetSocketContext must be used within a FleetSocketProvider');
  return ctx;
}

/** Convenience hook: subscribe to one message type for the lifetime of
 * the calling component, with automatic cleanup on unmount. */
export function useFleetSocketEvent<T = unknown>(
  type: FleetSocketMessage['type'],
  handler: (payload: T) => void,
) {
  const { subscribe } = useFleetSocketContext();
  useEffect(() => {
    return subscribe((message) => {
      if (message.type === type) handler(message.payload as T);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, subscribe]);
}
