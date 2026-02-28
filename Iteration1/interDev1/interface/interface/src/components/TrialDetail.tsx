import React from "react";
import { useParams } from "react-router-dom";
import { Box, Heading, Text, SimpleGrid, Button } from "@chakra-ui/react";
import { Trial } from "../hooks/useTrials";

interface Props {
  trial: Trial;
}

const TrialDetail = ({ trial }: Props) => {
  const { projectName } = useParams(); // Logic to fetch the trial based on projectName

  // Helper function to create a box for a group of trial information
  const renderInfoGroup = (
    title: string,
    details: Array<{ label: string; value: string | undefined }>,
    borderWidth: string = "1px",
    mb: number = 2
  ) => {
    return (
      <Box p={4} borderWidth={borderWidth} borderRadius="lg">
        <Heading as="h3" size="md" mb={2}>
          {title}
        </Heading>
        {details.map(({ label, value }) => (
          <Text key={label}>
            <b>{label}:</b> {value || "Not available"}
          </Text>
        ))}
      </Box>
    );
  };

  return (
    <Box width="95%" marginX="auto">
      <Box p={4} borderWidth="1px" borderRadius="lg" mb={6}>
        <Heading as="h1" size="lg" mb={4}>
          {trial.Title}
        </Heading>
        {renderInfoGroup(
          "Basic Information",
          [
            { label: "Abstract", value: trial.Abstract },
            { label: "Authors", value: trial.Authors },
          ],
          "0px",
          0
        )}
      </Box>
      <SimpleGrid columns={{ sm: 1, md: 2, lg: 3 }} spacing={5}>
        {renderInfoGroup("Geographic Data", [
          { label: "Country Code", value: trial.countryCode },
          { label: "State/Province", value: trial.State_Province_name },
        ])}
        {renderInfoGroup("Project Details", [
          { label: "Sector", value: trial.Sector },
          { label: "Sub-sector", value: trial.Sub_sector },
          {
            label: "Implementation Agency",
            value: trial.Implementation_agency,
          },
          { label: "Project Name", value: trial.Project_name },
        ])}
        {renderInfoGroup("Ethics and Evaluation", [
          { label: "Ethics Approval", value: trial.Ethics_Approval },
          { label: "Evaluation Design", value: trial.Evaluation_design },
        ])}
        {renderInfoGroup("Access and Registration", [
          { label: "Open Access", value: trial.Open_Access },
          { label: "Pre Registration", value: trial.Pre_Registration },
        ])}
        {renderInfoGroup("Data and Methodology", [
          {
            label: "Primary Dataset Availability",
            value: trial.Primary_Dataset_Availability,
          },
          { label: "Mixed Method", value: trial.Mixed_method },
        ])}
        {renderInfoGroup("Additional Details", [
          { label: "Language", value: trial.Language },
          { label: "Keywords", value: trial.Keywords },
          { label: "Unit of Observation", value: trial.Unit_of_observation },
          { label: "Equity Focus", value: trial.Equity_focus },
          {
            label: "CRS Voluntary DAC Code",
            value: trial.CRS_Voluntary_DAC_Code,
          },
        ])}
      </SimpleGrid>
    </Box>
  );
};

export default TrialDetail;
