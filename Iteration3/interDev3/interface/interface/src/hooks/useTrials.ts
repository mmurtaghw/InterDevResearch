// src/hooks/useTrials.ts

import axios, { AxiosRequestConfig } from "axios";
import qs from "qs";
import useData from "./useData";
import { Trial, TrialFilter } from "../types/trialTypes";

const DEFAULT_LIST_LIMIT = 60;

const useTrials = (filters: TrialFilter, trialIds?: string[]) => {
  const effectiveFilters = { ...filters };

  // Include trialIds in effectiveFilters if provided
  if (trialIds && trialIds.length > 0) {
    effectiveFilters.trialIds = trialIds;
  }

  // Ensure a default limit if not specified
  if (!effectiveFilters.limit) {
    effectiveFilters.limit = DEFAULT_LIST_LIMIT;
  }
  effectiveFilters.view = "summary";

  const serializedFilters = qs.stringify(effectiveFilters, {
    arrayFormat: "repeat",
    sort: (a, b) => a.localeCompare(b),
  });

  const requestConfig: AxiosRequestConfig = {
    params: effectiveFilters,
    paramsSerializer: (params) =>
      qs.stringify(params, { arrayFormat: "repeat" }),
  };

  // Fetch data using the custom hook with caching to avoid redundant refetches
  const shouldCache = !effectiveFilters.trialIds;
  const cacheOptions = shouldCache
    ? {
        cacheKey: `/knowledge_graph_data?${serializedFilters}`,
        staleTimeMs: Number.POSITIVE_INFINITY,
      }
    : undefined;

  const { data, error, isLoading } = useData<{ results: Trial[] }>(
    "/knowledge_graph_data",
    requestConfig,
    [serializedFilters],
    cacheOptions
  );

  // Return only the results array if data exists
  return { data: data?.results, error, isLoading };
};

export default useTrials;
