import { filter } from "@chakra-ui/react";
import { Category } from "./useCategories";
import useData from "./useData";
import qs from "qs";
import { AxiosRequestConfig } from "axios";

interface FetchGamesResponse {
  Abstract: string;
  CRS_Voluntary_DAC_Code: string;
}

export interface Trial {
  id: string;
  Abstract: string;
  Authors: string;
  CRS_Voluntary_DAC_Code: string;
  Equity_focus: string;
  Ethics_Approval: string;
  Evaluation_design: string;
  Implementation_agency: string;
  Keywords: string;
  Language: string;
  Mixed_method: string;
  Open_Access: string;
  Pre_Registration: string;
  Primary_Dataset_Availability: string;
  Project_name: string;
  Sector: string;
  State_Province_name: string;
  Sub_sector: string;
  Title: string;
  Unit_of_observation: string;
  countryCode: string;
}

export interface TrialFilter {
  limit: number;
  trialIds?: string[];
  Abstract?: string;
  Authors?: string;
  CRS_Voluntary_DAC_Code?: string;
  Equity_focus?: string;
  Sector?: string;
  countryCode?: string;
}

const useTrials = (filters: TrialFilter) => {
  const { trialIds, ...otherFilters } = filters;
  const effectiveFilters = { ...otherFilters, limit: filters.limit || 500 };

  // Use AxiosRequestConfig for proper typing
  const requestConfig: AxiosRequestConfig = {
    params: { ...effectiveFilters },
    paramsSerializer: (params) =>
      qs.stringify(params, { arrayFormat: "repeat" }),
  };

  // Add trialIds to the query parameters if they exist
  if (trialIds && trialIds.length > 0) {
    requestConfig.params = { ...requestConfig.params, trialIds };
  }

  console.log(requestConfig.params.trialIds);
  return useData<Trial>("/knowledge_graph_data", requestConfig, [filters]);
};

export default useTrials;
