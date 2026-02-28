// useCategories.ts

import { useState, useEffect } from "react";
import apiClient from "../services/api-client-trials";

export interface Category {
  name: string;
  value?: string;
}

interface UseCategoriesResult {
  data: Category[] | undefined;
  isLoading: boolean;
  error: any;
}

function useCategories(categoryTypeToFetch?: string): UseCategoriesResult {
  const [data, setData] = useState<Category[] | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    // Ensure the categoryTypeToFetch is defined, with a default fallback
    const categoryType = categoryTypeToFetch || "Sector";

    apiClient
      .get(`/categories`, {
        params: { category: categoryType },
      })
      .then((response) => {
        // Ensure the data structure matches what is expected
        setData(response.data.results || []);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching categories:", err);
        setError(err);
        setIsLoading(false);
      });
  }, [categoryTypeToFetch]);

  return { data, isLoading, error };
}

export default useCategories;
