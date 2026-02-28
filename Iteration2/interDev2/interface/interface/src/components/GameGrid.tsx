import React from "react";
import { Spinner, Text, VStack, SimpleGrid } from "@chakra-ui/react";
import useTrials from "../hooks/useTrials";
import TrialCard from "./GameCard";
import { Trial, TrialFilter } from "../types/trialTypes";
import { CollectionType } from "../types/collectionTypes";

interface GameGridProps {
  trialFilter: TrialFilter;
  trialIds?: string[];
  onSelectTrial: (selectedTrial: Trial) => void;
  onAddTrialToCollection: (trialId: string, collectionName: string) => void;
  onRemoveTrialFromCollection: (
    trialId: string,
    collectionName: string
  ) => void;
  isTrialInCollection: (trialId: string, collectionName: string) => boolean;
  collections: CollectionType[];
}

const GameGrid: React.FC<GameGridProps> = ({
  trialFilter,
  trialIds,
  onSelectTrial,
  onAddTrialToCollection,
  onRemoveTrialFromCollection,
  isTrialInCollection,
  collections,
}) => {
  const { data, isLoading, error } = useTrials(trialFilter, trialIds);

  if (isLoading) {
    return (
      <VStack spacing={4} align="center" justify="center" height="100%">
        <Spinner size="xl" />
        <Text>Loading trials...</Text>
      </VStack>
    );
  }

  if (error) {
    return (
      <VStack spacing={4} align="center" justify="center" height="100%">
        <Text fontSize="lg" color="red.500">
          Error: {error}
        </Text>
      </VStack>
    );
  }

  if (!data || data.length === 0) {
    return (
      <VStack spacing={4} align="center" justify="center" height="100%">
        <Text>No trials found.</Text>
      </VStack>
    );
  }

  return (
    <VStack spacing={4} align="stretch" padding={4}>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
        {data.map((trial) => (
          <TrialCard
            key={trial.id}
            trial={trial}
            onSelectTrial={onSelectTrial}
            onAddToCollection={onAddTrialToCollection}
            onRemoveFromCollection={onRemoveTrialFromCollection}
            isInCollection={(collectionName) =>
              isTrialInCollection(trial.id, collectionName)
            }
            collections={collections}
          />
        ))}
      </SimpleGrid>
    </VStack>
  );
};

export default GameGrid;
