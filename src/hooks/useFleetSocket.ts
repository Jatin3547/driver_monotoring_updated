import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE_URL } from '@/services/config';

export type WebSocketStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface FleetSocketMessage<T = unknown> {
  type: 'gps_update' | 'monitoring_update' | 'safety_event' | 'incident_created' | 'alert_created';
  payload: T;
}

type Listener = (message: FleetSocketMessage) => void;

const RECONNECT_DELAY_MS = 3000;

function wsUrl(): string {
  // API_BASE_URL is e.g. "http://127.0.0.1:8000/api" -> ws://127.0.0.1:8000/api/ws
  const httpUrl = new URL('ws', API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`);
  httpUrl.protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  return httpUrl.toString();
}

/**
 * Single shared-per-hook-instance WebSocket connection to the backend's
 * /api/ws endpoint. Handles auto-reconnect with a fixed backoff, exposes
 * connection status, and lets callers subscribe to typed messages.
 *
 * Intentionally does NOT open a connection when the app is running in
 * mock mode — there is no backend to connect to, and this avoids a
 * console full of failed-connection noise in the default demo.
 */
export function useFleetSocket(enabled: boolean) {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const socketRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Set<Listener>>(new Set());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedByUsRef = useRef(false);

  const subscribe = useCallback((listener: Listener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    closedByUsRef.current = false;

    function connect() {
      setStatus((prev) => (prev === 'disconnected' ? 'connecting' : 'reconnecting'));
      let socket: WebSocket;
      try {
        socket = new WebSocket(wsUrl());
      } catch {
        setStatus('disconnected');
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => setStatus('connected');

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as FleetSocketMessage;
          listenersRef.current.forEach((listener) => listener(message));
        } catch {
          // Ignore malformed frames rather than crash the app.
        }
      };

      socket.onerror = () => {
        // onclose fires right after; reconnection is handled there.
      };

      socket.onclose = () => {
        if (closedByUsRef.current) {
          setStatus('disconnected');
          return;
        }
        setStatus('reconnecting');
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      closedByUsRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [enabled]);

  return { status, subscribe };
}
