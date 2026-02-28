import { SimpleGrid, Text, Box } from "@chakra-ui/react";
import useTrials, { Trial, TrialFilter } from "../hooks/useTrials";
import GameCard from "./GameCard";
import GameCardSkeleton from "./GameCardSkeleton";
import GameCardContainer from "./GameCardContainer";
import React, { useMemo } from "react";

interface Props {
  trialFilter: TrialFilter;
  trialIds?: string[]; // Optional array of trial IDs
  onSelectTrial: (selectedTrial: Trial) => void;
  onAddTrialToCollection: (selectedTrial: string) => void;
  onRemoveTrialFromCollection: (selectedTrial: string) => void;
  isInCollection: (trialId: string) => boolean;
}

const GameGrid = ({
  trialFilter,
  trialIds,
  onSelectTrial,
  onAddTrialToCollection,
  isInCollection,
  onRemoveTrialFromCollection,
}: Props) => {
  // Include trialIds in the filter if they are provided
  const effectiveFilter = useMemo(() => {
    const trials =
      trialIds && trialIds.length > 0
        ? { ...trialFilter, trialIds }
        : trialFilter;
    return trials;
  }, [trialFilter, trialIds]);

  const { data, error, isLoading } = useTrials(effectiveFilter);
  const skeletons = [1, 2, 3, 4, 5, 6];

  // Check if trialIds is an empty array
  if (trialIds && trialIds.length === 0) {
    return <Box padding={10}>No trials to display.</Box>;
  }

  return (
    <>
      {error && <Text>{error}</Text>}
      <SimpleGrid
        columns={{ sm: 1, md: 2, lg: 3, xl: 4 }}
        padding={10}
        spacing={3}
      >
        {isLoading &&
          skeletons.map((skeleton) => (
            <GameCardContainer key={skeleton}>
              <GameCardSkeleton />
            </GameCardContainer>
          ))}

        {data &&
          data.map((trial) => (
            <GameCardContainer key={trial.id}>
              <GameCard
                game={trial}
                onSelectTrial={onSelectTrial}
                onAddTrialToCollection={onAddTrialToCollection}
                isInCollection={isInCollection}
                onRemoveTrialFromCollection={onRemoveTrialFromCollection}
              />
            </GameCardContainer>
          ))}
      </SimpleGrid>
    </>
  );
};

export default GameGrid;
