// src/types/trialTypes.ts

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
  Protocol_Pre_Analysis_Plan: string;
  Sector: string;
  State_Province_name: string;
  Sub_sector: string;
  Title: string;
  Unit_of_observation: string;
  DOI?: string;
  paperUrl?: string;
  publicationTitle?: string;
  countryCode: string;
  hasExternalClassification: string;
  hasMethod: string;
  hasOutcome: string;
  hasPublicationInfo: string;
  lat: string;
  long: string;
  name: string;
  population: string;
  type: string;
}

export interface TrialFilter {
  limit?: number;
  trialIds?: string[];
  view?: string;
  Abstract?: string | string[];
  Authors?: string | string[];
  CRS_Voluntary_DAC_Code?: string | string[];
  Equity_focus?: string | string[];
  Sector?: string | string[];
  Sub_sector?: string | string[];
  Evaluation_design?: string | string[];
  Program_funding_agency?: string | string[];
  Implementation_agency?: string | string[];
  countryCode?: string | string[];
  search?: string;
}
