// src/components/TrialCard.tsx

import React from "react";
import {
  Box,
  Text,
  Button,
  VStack,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast, // Import useToast from Chakra UI
} from "@chakra-ui/react";
import { Trial } from "../types/trialTypes";
import { CollectionType } from "../types/collectionTypes";

interface SelectionContext {
  source: "evidence" | "collection";
  collectionName?: string;
}

interface TrialCardProps {
  trial: Trial;
  onSelectTrial: (selectedTrial: Trial, context?: SelectionContext) => void;
  onAddToCollection: (trialId: string, collectionName: string) => void;
  onRemoveFromCollection: (trialId: string, collectionName: string) => void;
  isInCollection: (collectionName: string) => boolean;
  collections: CollectionType[];
  selectContext?: SelectionContext;
}

const TrialCard: React.FC<TrialCardProps> = ({
  trial,
  onSelectTrial,
  onAddToCollection,
  onRemoveFromCollection,
  isInCollection,
  collections,
  selectContext,
}) => {
  const toast = useToast(); // Initialize Chakra UI's toast hook

  const truncatedAbstract =
    trial.Abstract.length > 150
      ? `${trial.Abstract.substring(0, 150)}...`
      : trial.Abstract;

  const handleAddOrRemove = (collectionName: string) => {
    if (isInCollection(collectionName)) {
      onRemoveFromCollection(trial.id, collectionName);
      toast({
        title: "Trial Removed",
        description: `The trial has been removed from the collection: ${collectionName}.`,
        status: "warning",
        duration: 3000,
        isClosable: true,
        position: "top-right",
      });
    } else {
      onAddToCollection(trial.id, collectionName);
      toast({
        title: "Trial Added",
        description: `The trial has been added to the collection: ${collectionName}.`,
        status: "success",
        duration: 3000,
        isClosable: true,
        position: "top-right",
      });
    }
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" overflow="hidden" p="4">
      <VStack spacing={3} align="start">
        <Text fontWeight="bold">{trial.Title}</Text>
        <Text fontSize="sm">{trial.Authors}</Text>
        <Text fontSize="sm">{truncatedAbstract}</Text>

        <Button onClick={() => onSelectTrial(trial, selectContext)}>
          View Details
        </Button>

        {/* Dropdown Menu for Collection Management */}
        <Menu>
          <MenuButton as={Button} colorScheme="blue">
            Add to Collection
          </MenuButton>
          <MenuList>
            {/* Create new collection option */}
            <MenuItem
              onClick={() => {
                const newCollection = prompt("Enter new collection name");
                if (newCollection) {
                  handleAddOrRemove(newCollection);
                }
              }}
            >
              Create New Collection
            </MenuItem>

            {/* Existing collections */}
            {collections.map((collection) => (
              <MenuItem
                key={collection.name}
                onClick={() => handleAddOrRemove(collection.name)}
              >
                {isInCollection(collection.name)
                  ? `Remove from ${collection.name}`
                  : `Add to ${collection.name}`}
              </MenuItem>
            ))}
          </MenuList>
        </Menu>
      </VStack>
    </Box>
  );
};

export default TrialCard;
