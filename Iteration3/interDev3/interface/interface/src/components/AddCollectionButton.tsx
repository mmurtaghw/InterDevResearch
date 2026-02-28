// src/components/AddCollectionButton.tsx

import React, { useState } from "react";
import { Button, Select, Input, VStack } from "@chakra-ui/react";
import { CollectionType } from "../types/collectionTypes";
import { Trial } from "../types/trialTypes";

interface Props {
  trial: Trial;
  collections: CollectionType[];
  onAddTrialToCollection: (trialId: string, collectionName: string) => void;
  onCreateCollection: (name: string) => void;
}

export const AddCollectionButton: React.FC<Props> = ({
  trial,
  collections,
  onAddTrialToCollection,
  onCreateCollection,
}) => {
  const [selectedCollection, setSelectedCollection] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("");

  const handleAddToCollection = () => {
    const newCollection = newCollectionName.trim();
    if (newCollection) {
      // User wants to create a new collection
      onCreateCollection(newCollection);
      onAddTrialToCollection(trial.id, newCollection);
      setNewCollectionName("");
      setSelectedCollection("");
    } else if (selectedCollection) {
      // User wants to add to an existing collection
      onAddTrialToCollection(trial.id, selectedCollection);
      setSelectedCollection("");
    } else {
      // No collection selected or entered
      alert("Please select or enter a collection name.");
    }
  };

  return (
    <VStack spacing={2} align="stretch">
      <Select
        placeholder="Select Collection"
        value={selectedCollection}
        onChange={(e) => setSelectedCollection(e.target.value)}
        isDisabled={newCollectionName.trim().length > 0}
      >
        {collections.map((collection) => (
          <option key={collection.name} value={collection.name}>
            {collection.name}
          </option>
        ))}
      </Select>
      <Input
        placeholder="Or create new collection"
        value={newCollectionName}
        onChange={(e) => setNewCollectionName(e.target.value)}
        isDisabled={selectedCollection.length > 0}
      />
      <Button onClick={handleAddToCollection} colorScheme="blue">
        Add to Collection
      </Button>
    </VStack>
  );
};

export default AddCollectionButton;
