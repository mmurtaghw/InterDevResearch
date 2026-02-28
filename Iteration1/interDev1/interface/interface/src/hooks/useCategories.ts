import useData from "./useData";

export interface Category {
  name: string | undefined;
  code?: string;
}

const useCategories = (categoryType: string = "Sector") => {
  //Case where undefined
  if (categoryType === undefined) {
    categoryType = "Sector";
  }
  // Create a request configuration object with query parameters
  const requestConfig = {
    params: {
      category: categoryType,
    },
  };

  // Use the base URL for the endpoint
  const url = "/categories";

  return useData<Category>(url, requestConfig);
};

export default useCategories;
