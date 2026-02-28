// src/hooks/useTrials.ts

import axios, { AxiosRequestConfig } from "axios";
import qs from "qs";
import useData from "./useData";
import { Trial, TrialFilter } from "../types/trialTypes";

const useTrials = (filters: TrialFilter, trialIds?: string[]) => {
  const effectiveFilters = { ...filters };

  // Include trialIds in effectiveFilters if provided
  if (trialIds && trialIds.length > 0) {
    effectiveFilters.trialIds = trialIds;
  }

  // Ensure a default limit if not specified
  if (!effectiveFilters.limit) {
    effectiveFilters.limit = 150;
  }

  const requestConfig: AxiosRequestConfig = {
    params: effectiveFilters,
    paramsSerializer: (params) =>
      qs.stringify(params, { arrayFormat: "repeat" }),
  };

  // Fetch data using the custom hook
  const { data, error, isLoading } = useData<{ results: Trial[] }>(
    "/knowledge_graph_data",
    requestConfig,
    [JSON.stringify(effectiveFilters)]
  );

  // Return only the results array if data exists
  return { data: data?.results, error, isLoading };
};

export default useTrials;
