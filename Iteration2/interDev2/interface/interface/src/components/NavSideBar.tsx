import { Box } from "@chakra-ui/react";
import React from "react";
import CategoryHolder from "./CategoryHolder";
import { TrialFilter } from "../types/trialTypes";

interface Props {
  typeFilter: TrialFilter;
  setSelectedFilter: (selectedFilter: TrialFilter) => void;
}

const NavSideBar: React.FC<Props> = ({ typeFilter, setSelectedFilter }) => {
  return (
    <Box paddingX={5}>
      {/* Control overflow */}
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Sector)
            ? typeFilter.Sector[0]
            : typeFilter.Sector
        }
        categoryName="Sector"
        categoryTypeToFetch="Sector"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Sector: category === null ? undefined : category.value || category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.countryCode)
            ? typeFilter.countryCode[0]
            : typeFilter.countryCode
        }
        categoryName="Country"
        categoryTypeToFetch="Countrycode"
        onSelectCategory={(countryCode) =>
          setSelectedFilter({
            ...typeFilter,
            countryCode:
              countryCode === null ? undefined : countryCode.value || countryCode.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Methodology)
            ? typeFilter.Methodology[0]
            : typeFilter.Methodology
        }
        categoryName="Methodology"
        categoryTypeToFetch="Methodology"
        onSelectCategory={(methodology) =>
          setSelectedFilter({
            ...typeFilter,
            Methodology:
              methodology === null ? undefined : methodology.value || methodology.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.InterventionType)
            ? typeFilter.InterventionType[0]
            : typeFilter.InterventionType
        }
        categoryName="Intervention Type"
        categoryTypeToFetch="InterventionType"
        onSelectCategory={(interventionType) =>
          setSelectedFilter({
            ...typeFilter,
            InterventionType:
              interventionType === null
                ? undefined
                : interventionType.value || interventionType.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.OutcomeDomain)
            ? typeFilter.OutcomeDomain[0]
            : typeFilter.OutcomeDomain
        }
        categoryName="Outcome Domain"
        categoryTypeToFetch="OutcomeDomain"
        onSelectCategory={(outcomeDomain) =>
          setSelectedFilter({
            ...typeFilter,
            OutcomeDomain:
              outcomeDomain === null ? undefined : outcomeDomain.value || outcomeDomain.name,
          })
        }
      />
    </Box>
  );
};

export default NavSideBar;
