import { GridItem, Show } from "@chakra-ui/react";
import React from "react";
import CategoryHolder from "./CategoryHolder";
import { TrialFilter, Trial } from "../hooks/useTrials";

interface Props {
  typeFilter: TrialFilter;
  setSelectedFilter: (selectedFilter: TrialFilter) => void;
}
const NavSideBar = ({ typeFilter, setSelectedFilter }: Props) => {
  return (
    <Show above="lg">
      <GridItem area="aside" paddingX={5}>
        {" "}
        {/* Control overflow */}
        <CategoryHolder
          selectedCategory={typeFilter.Sector}
          categoryName="Sector"
          categoryTypeToFetch="Sector"
          onSelectCategory={(category) =>
            setSelectedFilter({
              ...typeFilter,
              Sector: category === null ? undefined : category.name,
            })
          }
        />
        <CategoryHolder
          selectedCategory={typeFilter.countryCode}
          categoryName="Country"
          categoryTypeToFetch="Countrycode"
          onSelectCategory={(countryCode) =>
            setSelectedFilter({
              ...typeFilter,
              countryCode:
                countryCode === null
                  ? undefined
                  : countryCode.code || countryCode.name,
            })
          }
        />
      </GridItem>
    </Show>
  );
};

export default NavSideBar;
