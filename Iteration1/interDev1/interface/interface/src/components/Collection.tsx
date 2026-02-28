import React, { useState } from "react";
import GameGrid from "./GameGrid";
import { Trial, TrialFilter } from "../hooks/useTrials";

interface Props {
  onSelectTrial: (selectedTrial: Trial) => void;
  onAddTrialToCollection: (selectedTrial: string) => void;
  onRemoveTrialFromCollection: (selectedTrial: string) => void;
  isInCollection: (trialId: string) => boolean;
  trialFilter: TrialFilter;
  trialIds: string[];
}

const Collection = ({
  onSelectTrial,
  trialFilter,
  trialIds,
  onAddTrialToCollection,
  onRemoveTrialFromCollection,
  isInCollection,
}: Props) => {
  return (
    <GameGrid
      trialFilter={trialFilter}
      onSelectTrial={onSelectTrial}
      trialIds={trialIds}
      onAddTrialToCollection={onAddTrialToCollection}
      onRemoveTrialFromCollection={onRemoveTrialFromCollection}
      isInCollection={isInCollection}
    ></GameGrid>
  );
};

export default Collection;
