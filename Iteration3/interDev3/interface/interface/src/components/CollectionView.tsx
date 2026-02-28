import React, { useState } from "react";
import { VStack, Button, Box, Heading, Select } from "@chakra-ui/react";
import GameGrid from "./GameGrid";
import ChatPanel from "./ChatPanel";
import { Trial, TrialFilter } from "../types/trialTypes";
import { CollectionType } from "../types/collectionTypes";
import { useChatMode } from "../context/ChatModeContext";

export interface Props {
  collectionName: string;
  collections: CollectionType[];
  onSelectTrial: (
    selectedTrial: Trial,
    context?: { source: "evidence" | "collection"; collectionName?: string }
  ) => void;
  onAddTrialToCollection: (trialId: string, collectionName: string) => void;
  onRemoveTrialFromCollection: (
    trialId: string,
    collectionName: string
  ) => void;
  isTrialInCollection: (trialId: string, collectionName: string) => boolean;
  trialFilter: TrialFilter;
  downloadCollection: (collectionName: string, format: string) => void;
}

const CollectionView: React.FC<Props> = ({
  collectionName,
  collections,
  onSelectTrial,
  onAddTrialToCollection,
  onRemoveTrialFromCollection,
  isTrialInCollection,
  trialFilter,
  downloadCollection,
}) => {
  const collection = collections.find((col) => col.name === collectionName);
  const trialIds = collection ? collection.trialIds : [];
  const { chatMode } = useChatMode();
  const showChat = chatMode !== "none";
  const showSources = chatMode === "chat-sources";

  // State for the selected download format: "turtle" or "csv"
  const [downloadFormat, setDownloadFormat] = useState<string>("turtle");

  return (
    <VStack spacing={4} align="stretch" padding={4}>
      <Heading as="h2" size="lg">
        Collection: {collectionName}
      </Heading>
      <Box display="flex" alignItems="center">
        <Select
          width="150px"
          mr={2}
          value={downloadFormat}
          onChange={(e) => setDownloadFormat(e.target.value)}
        >
          <option value="turtle">Turtle</option>
          <option value="csv">CSV</option>
        </Select>
        <Button
          colorScheme="green"
          size="md"
          onClick={() => downloadCollection(collectionName, downloadFormat)}
          isDisabled={!collection || collection.trialIds.length === 0}
        >
          Download Collection
        </Button>
      </Box>
      {/* LLM-powered chat about this collection */}
      {showChat && (
        <ChatPanel
          trialIds={trialIds}
          title={`Chat about ${collectionName}`}
          showSources={showSources}
          collectionName={collectionName}
        />
      )}

      {collection && collection.trialIds.length > 0 ? (
        <GameGrid
          trialFilter={trialFilter}
          trialIds={trialIds} // Pass the trialIds prop here
          onAddTrialToCollection={(trialId) =>
            onAddTrialToCollection(trialId, collectionName)
          }
          onRemoveTrialFromCollection={(trialId) =>
            onRemoveTrialFromCollection(trialId, collectionName)
          }
          isTrialInCollection={(trialId) =>
            isTrialInCollection(trialId, collectionName)
          }
          collections={collections}
          selectContext={{ source: "collection", collectionName }}
          onSelectTrial={(trial) =>
            onSelectTrial(trial, { source: "collection", collectionName })
          }
        />
      ) : (
        <Box padding={4}>No trials in this collection.</Box>
      )}
    </VStack>
  );
};

export default CollectionView;
