import { useEffect, useState, useCallback } from 'react';
import type { AsyncStatus } from '@/types';

interface UseAsyncDataResult<T> {
  data: T | undefined;
  status: AsyncStatus;
  error: string | undefined;
  refetch: () => void;
}

export function useAsyncData<T>(fetcher: () => Promise<T>, deps: unknown[] = []): UseAsyncDataResult<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [error, setError] = useState<string | undefined>(undefined);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setError(undefined);

    fetcher()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setStatus('success');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Something went wrong');
        setStatus('error');
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { data, status, error, refetch };
}
