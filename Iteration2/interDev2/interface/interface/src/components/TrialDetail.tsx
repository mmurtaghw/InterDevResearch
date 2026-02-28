// TrialDetail.tsx

import React from "react";
import {
  VStack,
  Text,
  Box,
  Divider,
  Heading,
  useColorModeValue,
  useToast,
} from "@chakra-ui/react";
import { Trial } from "../types/trialTypes";
import AddCollectionButton from "./AddCollectionButton";
import { CollectionType } from "../types/collectionTypes";

interface Props {
  trial: Trial;
  collections: CollectionType[];
  onAddTrialToCollection: (trialId: string, collectionName: string) => void;
  onCreateCollection: (name: string) => void;
}

const TrialDetail: React.FC<Props> = ({
  trial,
  collections,
  onAddTrialToCollection,
  onCreateCollection,
}) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const textColor = useColorModeValue("gray.800", "white");
  const toast = useToast(); // Chakra UI's toast hook for notifications

  // Function to handle adding a trial to a collection with user feedback
  const handleAddToCollection = (trialId: string, collectionName: string) => {
    onAddTrialToCollection(trialId, collectionName);

    // Show feedback to the user
    toast({
      title: "Trial Added",
      description: `The trial has been added to the collection: ${collectionName}.`,
      status: "success",
      duration: 3000, // Duration in milliseconds
      isClosable: true,
      position: "top-right", // Display position
    });
  };

  return (
    <VStack
      spacing={6}
      align="stretch"
      padding={6}
      bg={bgColor}
      borderRadius="md"
      boxShadow="lg"
    >
      {/* Title Section */}
      <Box>
        <Heading size="lg" color={textColor} mb={2}>
          {trial.Title}
        </Heading>
        <Text fontSize="md" color="gray.500">
          {trial.Authors}
        </Text>
      </Box>

      <Divider />

      {/* Abstract Section */}
      {trial.Abstract && (
        <Box>
          <Heading size="md" color={textColor} mb={2}>
            Abstract
          </Heading>
          <Text color={textColor}>{trial.Abstract}</Text>
        </Box>
      )}

      <Divider />

      {/* Project Details Section */}
      <Box>
        <Heading size="md" color={textColor} mb={2}>
          Project Details
        </Heading>
        <Text color={textColor}>
          <strong>Project Name:</strong> {trial.Project_name || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Evaluation Design:</strong> {trial.Evaluation_design || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Sector:</strong> {trial.Sector || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Sub-sector:</strong> {trial.Sub_sector || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Implementation Agency:</strong>{" "}
          {trial.Implementation_agency || "N/A"}
        </Text>
      </Box>

      <Divider />

      {/* Geographic Information Section */}
      <Box>
        <Heading size="md" color={textColor} mb={2}>
          Geographic Information
        </Heading>
        <Text color={textColor}>
          <strong>Country Code:</strong> {trial.countryCode || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>State/Province:</strong> {trial.State_Province_name || "N/A"}
        </Text>
      </Box>

      <Divider />

      {/* Additional Information */}
      <Box>
        <Heading size="md" color={textColor} mb={2}>
          Additional Information
        </Heading>
        <Text color={textColor}>
          <strong>Unit of Observation:</strong>{" "}
          {trial.Unit_of_observation || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Language:</strong> {trial.Language || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Keywords:</strong> {trial.Keywords || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Open Access:</strong> {trial.Open_Access || "N/A"}
        </Text>
        <Text color={textColor}>
          <strong>Ethics Approval:</strong> {trial.Ethics_Approval || "N/A"}
        </Text>
      </Box>

      <Divider />

      {/* Add to Collection Button with updated handler */}
      <AddCollectionButton
        trial={trial}
        collections={collections}
        onAddTrialToCollection={handleAddToCollection} // Pass the handler that shows feedback
        onCreateCollection={onCreateCollection}
      />
    </VStack>
  );
};

export default TrialDetail;
