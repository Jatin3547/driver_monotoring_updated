import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE_URL } from '@/services/config';
import { getStoredToken } from '@/services/api/authService';

export type WebSocketStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface FleetSocketMessage<T = unknown> {
  type:
    | 'gps_update'
    | 'monitoring_update'
    | 'safety_event'
    | 'incident_created'
    | 'incident_deleted'
    | 'evidence_uploaded'
    | 'alert_created';
  payload: T;
}

type Listener = (message: FleetSocketMessage) => void;

const RECONNECT_DELAY_MS = 3000;

function wsUrl(): string {
  // API_BASE_URL is e.g. "http://127.0.0.1:8000/api" -> ws://127.0.0.1:8000/api/ws
  const httpUrl = new URL('ws', API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`);
  httpUrl.protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getStoredToken();
  if (token) httpUrl.searchParams.set('token', token);
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
      if (closedByUsRef.current) {
        return;
      }

      setStatus('connecting');
      const ws = new WebSocket(wsUrl());
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as FleetSocketMessage;
          for (const listener of listenersRef.current) {
            listener(parsed);
          }
        } catch {
          // Non-JSON message from server — ignore.
        }
      };

      ws.onerror = () => {
        // onerror is always followed by onclose, so reconnection is handled there.
      };

      ws.onclose = () => {
        socketRef.current = null;
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
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setStatus('disconnected');
    };
  }, [enabled]);

  return { status, subscribe };
}
