import React, { useState } from "react";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Text,
  Textarea,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
} from "@chakra-ui/react";
import { Trial } from "../hooks/useTrials";
import apiClient from "../services/api-client-trials";

const TrialSubmissionForm = () => {
  const [formData, setFormData] = useState<Trial>({
    id: "",
    Abstract: "",
    Authors: "",
    CRS_Voluntary_DAC_Code: "",
    Equity_focus: "",
    Ethics_Approval: "",
    Evaluation_design: "",
    Implementation_agency: "",
    Keywords: "",
    Language: "",
    Mixed_method: "",
    Open_Access: "",
    Pre_Registration: "",
    Primary_Dataset_Availability: "",
    Project_name: "",
    Sector: "",
    State_Province_name: "",
    Sub_sector: "",
    Title: "",
    Unit_of_observation: "",
    countryCode: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prevState) => ({
      ...prevState,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Form Data:", formData);

    try {
      const response = await apiClient.post("/add_knowledge_graph_entry", formData);
      const data = response.data;
      console.log("Success:", data);
      // Optionally reset form or handle success state
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <Box p={4}>
      <Heading as="h1" size="xl" mb={4}>
        Trial Submission Form
      </Heading>
      <Text fontSize="md" mb={8}>
        Please fill in the details of the trial in the form below. Ensure all
        required fields are completed before submitting.
      </Text>

      <Box as="form" onSubmit={handleSubmit}>
        {/* First Card for Abstract, Authors, Title, and Project Name */}
        <Card mb={6}>
          <CardHeader>
            <Heading size="md">Basic Info</Heading>
          </CardHeader>
          <CardBody>
            <FormControl id="Abstract" isRequired>
              <FormLabel>Abstract</FormLabel>
              <Textarea
                name="Abstract"
                value={formData.Abstract}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="Authors" isRequired mt={4}>
              <FormLabel>Authors</FormLabel>
              <Input
                name="Authors"
                value={formData.Authors}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="Title" isRequired mt={4}>
              <FormLabel>Title</FormLabel>
              <Input
                name="Title"
                value={formData.Title}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="Project_name" isRequired mt={4}>
              <FormLabel>Project Name</FormLabel>
              <Input
                name="Project_name"
                value={formData.Project_name}
                onChange={handleChange}
              />
            </FormControl>
          </CardBody>
        </Card>

        <Card mb={6}>
          <CardHeader>
            <Heading size="md">Evaluation Design</Heading>
          </CardHeader>
          <CardBody>
            <FormControl id="Evaluation_design" isRequired mt={4}>
              <FormLabel>Evaluation Design</FormLabel>
              <Input
                name="Evaluation_design"
                value={formData.Evaluation_design}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="Implementation_agency" isRequired mt={4}>
              <FormLabel>Implementation Agency</FormLabel>
              <Input
                name="Implementation_agency"
                value={formData.Implementation_agency}
                onChange={handleChange}
              />
            </FormControl>
          </CardBody>
        </Card>

        <Card mb={6}>
          <CardHeader>
            <Heading size="md">Geographic Information</Heading>
          </CardHeader>
          <CardBody>
            <FormControl id="countryCode" isRequired mt={4}>
              <FormLabel>Country</FormLabel>
              <Input
                name="countryCode"
                value={formData.countryCode}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="State_Province_name" isRequired mt={4}>
              <FormLabel>State or Province</FormLabel>
              <Input
                name="State_Province_name"
                value={formData.State_Province_name}
                onChange={handleChange}
              />
            </FormControl>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <Heading size="md">Project Info</Heading>
          </CardHeader>
          <CardBody>
            <FormControl id="Sector" isRequired mt={4}>
              <FormLabel>Sector</FormLabel>
              <Input
                name="Sector"
                value={formData.Sector}
                onChange={handleChange}
              />
            </FormControl>
            <FormControl id="Unit_of_observation" isRequired mt={4}>
              <FormLabel>Unit of Observation</FormLabel>
              <Input
                name="Unit_of_observation"
                value={formData.Unit_of_observation}
                onChange={handleChange}
              />
            </FormControl>
          </CardBody>
          <CardFooter>
            <Button colorScheme="blue" type="submit">
              Submit
            </Button>
          </CardFooter>
        </Card>
      </Box>
    </Box>
  );
};

export default TrialSubmissionForm;
