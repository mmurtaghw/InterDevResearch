// useData.ts

import { useState, useEffect } from "react";
import axios, { AxiosRequestConfig } from "axios";
import apiClient from "../services/api-client-trials";

type CacheEntry<T> = {
  data: T;
  timestamp: number;
};

type UseDataOptions = {
  cacheKey?: string;
  /**
   * Time in milliseconds before cached data is considered stale.
   * Defaults to Infinity when a cacheKey is provided.
   */
  staleTimeMs?: number;
};

const responseCache = new Map<string, CacheEntry<unknown>>();

// Define the shape of the data returned by the API
export interface UseDataResult<T> {
  data: T | undefined;
  error: string | null;
  isLoading: boolean;
}

function useData<T>(
  url: string,
  config: AxiosRequestConfig = {}, // Make config optional with a default empty object
  deps: any[] = [], // Make deps optional with a default empty array
  options: UseDataOptions = {}
): UseDataResult<T> {
  const { cacheKey, staleTimeMs } = options;
  const normalizedStaleTime =
    cacheKey && staleTimeMs === undefined ? Number.POSITIVE_INFINITY : staleTimeMs;

  const readCacheEntry = (): CacheEntry<T> | undefined => {
    if (!cacheKey) return undefined;
    return responseCache.get(cacheKey) as CacheEntry<T> | undefined;
  };

  const isEntryFresh = (entry?: CacheEntry<T>) => {
    if (!entry) return false;
    if (!cacheKey) return false;
    if (!normalizedStaleTime || normalizedStaleTime <= 0) return false;
    if (!Number.isFinite(normalizedStaleTime)) return true;
    return Date.now() - entry.timestamp < normalizedStaleTime;
  };

  const initialCache = readCacheEntry();
  const [data, setData] = useState<T | undefined>(() =>
    isEntryFresh(initialCache) ? initialCache?.data : initialCache?.data ?? undefined
  );
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(
    () => !initialCache || !isEntryFresh(initialCache)
  );

  const effectDeps = cacheKey ? [...deps, cacheKey] : deps;

  useEffect(() => {
    let isMounted = true;
    const cached = readCacheEntry();

    if (isEntryFresh(cached)) {
      setError(null);
      setData(cached?.data);
      setIsLoading(false);
      return () => {
        isMounted = false;
      };
    }

    if (cached?.data && data !== cached.data) {
      // Reuse stale data while refetching to avoid flashes
      setData(cached.data);
    }

    const fetchData = async () => {
      setIsLoading(!cached?.data);
      setError(null);
      try {
        const response = await apiClient.get<T>(url, config);
        if (!isMounted) return;
        setData(response.data);
        if (cacheKey) {
          responseCache.set(cacheKey, {
            data: response.data,
            timestamp: Date.now(),
          });
        }
      } catch (err: any) {
        if (!isMounted) return;
        console.error("API Error:", err);
        setError(err.message || "An unexpected error occurred.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, effectDeps); // Trigger the effect when dependencies change

  return { data, error, isLoading };
}

export default useData;
