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
            Sector:
              category === null
                ? undefined
                : category.value ?? category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Sub_sector)
            ? typeFilter.Sub_sector[0]
            : typeFilter.Sub_sector
        }
        categoryName="Sub-sector"
        categoryTypeToFetch="Sub-sector"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Sub_sector:
              category === null
                ? undefined
                : category.value ?? category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Evaluation_design)
            ? typeFilter.Evaluation_design[0]
            : typeFilter.Evaluation_design
        }
        categoryName="Evaluation Design"
        categoryTypeToFetch="Evaluation_design"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Evaluation_design:
              category === null
                ? undefined
                : category.value ?? category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Equity_focus)
            ? typeFilter.Equity_focus[0]
            : typeFilter.Equity_focus
        }
        categoryName="Equity Focus"
        categoryTypeToFetch="Equity_focus"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Equity_focus:
              category === null
                ? undefined
                : category.value ?? category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Program_funding_agency)
            ? typeFilter.Program_funding_agency[0]
            : typeFilter.Program_funding_agency
        }
        categoryName="Program Funding Agency"
        categoryTypeToFetch="Program_funding_agency"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Program_funding_agency:
              category === null
                ? undefined
                : category.value ?? category.name,
          })
        }
      />
      <CategoryHolder
        selectedCategory={
          Array.isArray(typeFilter.Implementation_agency)
            ? typeFilter.Implementation_agency[0]
            : typeFilter.Implementation_agency
        }
        categoryName="Implementation Agency"
        categoryTypeToFetch="Implementation_agency"
        onSelectCategory={(category) =>
          setSelectedFilter({
            ...typeFilter,
            Implementation_agency:
              category === null
                ? undefined
                : category.value ?? category.name,
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
        onSelectCategory={(country) =>
          setSelectedFilter({
            ...typeFilter,
            countryCode:
              country === null
                ? undefined
                : country.value ?? country.name,
          })
        }
      />
    </Box>
  );
};

export default NavSideBar;
