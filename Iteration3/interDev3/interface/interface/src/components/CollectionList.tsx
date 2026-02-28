// src/components/CollectionList.tsx

import React, { useState } from "react";
import { VStack, Button, Input, Box, Heading } from "@chakra-ui/react";
import { CollectionType } from "../types/collectionTypes";

interface Props {
  collections: CollectionType[];
  onCreateCollection: (name: string) => void;
  onSelectCollection: (name: string) => void;
}

const CollectionList: React.FC<Props> = ({
  collections,
  onCreateCollection,
  onSelectCollection,
}) => {
  const [newCollectionName, setNewCollectionName] = useState("");

  const handleCreateCollection = () => {
    const trimmedName = newCollectionName.trim();
    if (trimmedName !== "") {
      onCreateCollection(trimmedName);
      setNewCollectionName("");
    }
  };

  return (
    <VStack spacing={4} align="stretch" padding={4}>
      <Heading as="h2" size="lg" marginBottom={4}>
        Your Collections
      </Heading>
      {collections.length > 0 ? (
        collections.map((collection) => (
          <Button
            key={collection.name}
            onClick={() => onSelectCollection(collection.name)}
            variant="outline"
          >
            {collection.name}
          </Button>
        ))
      ) : (
        <Box>No collections available. Create one below!</Box>
      )}
      <Input
        placeholder="New Collection Name"
        value={newCollectionName}
        onChange={(e) => setNewCollectionName(e.target.value)}
      />
      <Button onClick={handleCreateCollection} colorScheme="blue">
        Create Collection
      </Button>
    </VStack>
  );
};

export default CollectionList;
