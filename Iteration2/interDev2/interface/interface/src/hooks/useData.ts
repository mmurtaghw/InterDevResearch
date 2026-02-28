// useData.ts

import { useState, useEffect } from "react";
import axios, { AxiosRequestConfig } from "axios";
import apiClient from "../services/api-client-trials";

// Define the shape of the data returned by the API
export interface UseDataResult<T> {
  data: T | undefined;
  error: string | null;
  isLoading: boolean;
}

function useData<T>(
  url: string,
  config: AxiosRequestConfig = {}, // Make config optional with a default empty object
  deps: any[] = [] // Make deps optional with a default empty array
): UseDataResult<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    // Function to fetch data
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<T>(url, config);
        setData(response.data);
      } catch (err: any) {
        console.error("API Error:", err);
        setError(err.message || "An unexpected error occurred.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps); // Trigger the effect when dependencies change

  return { data, error, isLoading };
}

export default useData;
