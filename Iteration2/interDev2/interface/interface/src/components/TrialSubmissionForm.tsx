import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Heading,
  Input,
  Textarea,
  Card,
  CardHeader,
  CardBody,
  Alert,
  AlertIcon,
  Select,
  Spinner,
  Text,
} from "@chakra-ui/react";
import axios from "axios";
import { getNames, getCode } from "country-list";

type TrialFormType = {
  QualtricsID: string; // New field for Qualtrics ID
  Abstract: string;
  Authors: string;
  CRS_Voluntary_DAC_Code: string;
  Equity_focus: string;
  Ethics_Approval: string;
  Evaluation_design: string;
  Implementation_agency: string;
  Keywords: string;
  Language: string;
  Mixed_method: string;
  Open_Access: string;
  Pre_Registration: string;
  Primary_Dataset_Availability: string;
  // Removed Project_name field
  Sector: string;
  State_Province_name: string;
  Sub_sector: string;
  Title: string;
  Unit_of_observation: string;
  countryCode: string;
  countryName: string;
  population: string;
  latitude: string;
  longitude: string;
  Program_funding_agency: string;
  Research_funding_agency: string;
  Outcomes: string;
  Methodology: string;
  SelectedAI: string;
  UNSustainableGoals: string; // New field for UN Sustainable Goals
};

const TrialSubmissionForm = () => {
  const [formData, setFormData] = useState<TrialFormType>({
    QualtricsID: "", // Initialize Qualtrics ID
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
    // Removed Project_name from initial state
    Sector: "",
    State_Province_name: "",
    Sub_sector: "",
    Title: "",
    Unit_of_observation: "",
    countryCode: "",
    countryName: "",
    population: "",
    latitude: "",
    longitude: "",
    Program_funding_agency: "",
    Research_funding_agency: "",
    Outcomes: "",
    Methodology: "",
    SelectedAI: "GPT",
    UNSustainableGoals: "",
  });

  const [submissionStatus, setSubmissionStatus] = useState<{
    success: boolean | null;
    message: string;
  }>({ success: null, message: "" });

  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [countryOptions, setCountryOptions] = useState<string[]>([]);

  useEffect(() => {
    setCountryOptions(getNames());
  }, []);

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prevState) => ({
      ...prevState,
      [name]: value,
    }));
  };

  const handleCountryChange = async (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const countryName = event.target.value;
    const countryCode = getCode(countryName);

    setFormData((prevState) => ({
      ...prevState,
      countryName,
      countryCode: countryCode || "",
    }));

    if (countryCode) {
      try {
        const response = await axios.get(
          `https://restcountries.com/v3.1/alpha/${countryCode}`
        );
        const countryData = response.data[0];

        setFormData((prevState) => ({
          ...prevState,
          population: countryData.population.toString(),
          latitude: countryData.latlng[0].toString(),
          longitude: countryData.latlng[1].toString(),
        }));
      } catch (error) {
        console.error("Error fetching country data:", error);
      }
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const uploadFormData = new FormData();
    uploadFormData.append("file", file);
    uploadFormData.append("selected_ai", formData.SelectedAI || "GPT");

    setIsUploading(true);
    try {
      const response = await axios.post(
        "https://interdev2.adaptcentre.ie/upload_pdf",
        uploadFormData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      if (response.data && response.data.response) {
        const parseResponse = await axios.post(
          "https://interdev2.adaptcentre.ie/parse_rdf",
          { rdf: response.data.response }
        );

        const parsedData = parseResponse.data;
        setFormData((prevState) => ({
          ...prevState,
          ...parsedData,
        }));
        setSubmissionStatus({
          success: true,
          message: "PDF processed and parsed successfully!",
        });
      }
    } catch (error) {
      setSubmissionStatus({
        success: false,
        message: "Failed to process PDF or parse RDF.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmissionStatus({ success: null, message: "" });

    const apiUrl = "https://interdev2.adaptcentre.ie/add_knowledge_graph_entry";
    try {
      const response = await axios.post(apiUrl, formData, {
        headers: { "Content-Type": "application/json" },
      });

      if (response.status !== 200) throw new Error("Failed to submit");

      setSubmissionStatus({
        success: true,
        message: "Trial submitted successfully!",
      });
      // Hide the form and display a thank-you message
      setIsSubmitted(true);
    } catch (error) {
      console.error("Error:", error);
      setSubmissionStatus({
        success: false,
        message: "Failed to submit trial. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box p={4}>
      <Heading as="h1" size="xl" mb={4}>
        Trial Submission Form
      </Heading>

      {submissionStatus.success !== null && (
        <Alert status={submissionStatus.success ? "success" : "error"} mb={4}>
          <AlertIcon />
          {submissionStatus.message}
        </Alert>
      )}

      {isSubmitted ? (
        <Box textAlign="center" mt={8}>
          <Heading as="h2" size="lg" mb={4}>
            Thank you for your submission!
          </Heading>
          <Text>Your trial has been submitted successfully.</Text>
        </Box>
      ) : (
        <>
          {/* Qualtrics ID Field */}
          <Card mb={6}>
            <CardHeader>
              <Heading size="md">Qualtrics ID</Heading>
            </CardHeader>
            <CardBody>
              <FormControl id="QualtricsID" isRequired>
                <FormLabel>Qualtrics ID</FormLabel>
                <FormHelperText>
                  Please enter your Qualtrics ID as per the instructions on the Qualtrics form.
                </FormHelperText>
                <Input
                  name="QualtricsID"
                  value={formData.QualtricsID}
                  onChange={handleChange}
                />
              </FormControl>
            </CardBody>
          </Card>

          {/* Select AI moved to the top */}
          <Card mb={6}>
            <CardHeader>
              <Heading size="md">Select AI</Heading>
            </CardHeader>
            <CardBody>
              <FormControl id="SelectedAI">
                <FormLabel>AI Provider</FormLabel>
                <FormHelperText>
                  Choose the AI provider to analyze your submission.
                </FormHelperText>
                <Select
                  name="SelectedAI"
                  value={formData.SelectedAI}
                  onChange={handleChange}
                >
                  <option value="GPT">GPT</option>
                  <option value="Google_Gemini">Google Gemini</option>
                  <option value="Claude_Anthropic">Claude Anthropic</option>
                </Select>
              </FormControl>
            </CardBody>
          </Card>

          {/* Upload PDF moved below Select AI */}
          <FormControl mb={4}>
            <FormLabel>Upload PDF</FormLabel>
            <FormHelperText>
              Upload a PDF document related to your trial.
            </FormHelperText>
            <Input type="file" accept=".pdf" onChange={handleFileUpload} />
            {isUploading && <Spinner mt={2} />}
          </FormControl>

          <Box as="form" onSubmit={handleSubmit}>
            {/* Basic Info */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Basic Info</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="Title" isRequired>
                  <FormLabel>Title</FormLabel>
                  <FormHelperText>
                    Enter the title of your trial.
                  </FormHelperText>
                  <Input
                    name="Title"
                    value={formData.Title}
                    onChange={handleChange}
                  />
                </FormControl>
                <FormControl id="Abstract" isRequired mt={4}>
                  <FormLabel>Abstract</FormLabel>
                  <FormHelperText>
                    Provide a brief summary of your trial.
                  </FormHelperText>
                  <Textarea
                    name="Abstract"
                    value={formData.Abstract}
                    onChange={handleChange}
                  />
                </FormControl>
                <FormControl id="Authors" isRequired mt={4}>
                  <FormLabel>Authors</FormLabel>
                  <FormHelperText>
                    List the trial authors. If multiple, separate by semicolons.
                  </FormHelperText>
                  <Input
                    name="Authors"
                    value={formData.Authors}
                    onChange={handleChange}
                  />
                </FormControl>
              </CardBody>
            </Card>

            {/* Additional Info for Sector, Keywords, and UN Sustainable Goals */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Additional Info</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="Sector" isRequired>
                  <FormLabel>Sector</FormLabel>
                  <FormHelperText>
                    Specify the main sector of your trial (e.g., Agriculture, Health).
                  </FormHelperText>
                  <Input
                    name="Sector"
                    value={formData.Sector}
                    onChange={handleChange}
                  />
                </FormControl>
                <FormControl id="Keywords" mt={4}>
                  <FormLabel>Keywords</FormLabel>
                  <FormHelperText>
                    Provide keywords (comma-separated) to help categorize your trial.
                  </FormHelperText>
                  <Input
                    name="Keywords"
                    value={formData.Keywords}
                    onChange={handleChange}
                  />
                </FormControl>
                <FormControl id="UNSustainableGoals" mt={4}>
                  <FormLabel>UN Sustainable Goals</FormLabel>
                  <FormHelperText>
                    Specify the UN Sustainable Goals relevant to this trial.
                  </FormHelperText>
                  <Input
                    name="UNSustainableGoals"
                    value={formData.UNSustainableGoals}
                    onChange={handleChange}
                  />
                </FormControl>
              </CardBody>
            </Card>

            {/* Outcomes */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Outcomes</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="Outcomes">
                  <FormLabel>Outcomes</FormLabel>
                  <FormHelperText>
                    List the outcomes of the trial, separated by semicolons.
                  </FormHelperText>
                  <Textarea
                    name="Outcomes"
                    value={formData.Outcomes}
                    onChange={handleChange}
                    placeholder="Enter outcomes separated by semicolons"
                  />
                </FormControl>
              </CardBody>
            </Card>

            {/* Methodology */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Methodology</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="Methodology">
                  <FormLabel>Methodology</FormLabel>
                  <FormHelperText>
                    Describe the methods and experimental design used in your trial.
                  </FormHelperText>
                  <Textarea
                    name="Methodology"
                    value={formData.Methodology}
                    onChange={handleChange}
                    placeholder="Enter methodology details"
                  />
                </FormControl>
              </CardBody>
            </Card>

            {/* Geographic Information */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Geographic Information</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="countryName" isRequired>
                  <FormLabel>Country</FormLabel>
                  <FormHelperText>
                    Select the country where the trial was conducted.
                  </FormHelperText>
                  <Select
                    name="countryName"
                    value={formData.countryName}
                    onChange={handleCountryChange}
                  >
                    <option value="">Select Country</option>
                    {countryOptions.map((country) => (
                      <option key={country} value={country}>
                        {country}
                      </option>
                    ))}
                  </Select>
                </FormControl>
                <FormControl id="countryCode" isReadOnly mt={4}>
                  <FormLabel>Country Code</FormLabel>
                  <FormHelperText>
                    This field is automatically populated based on your selection.
                  </FormHelperText>
                  <Input name="countryCode" value={formData.countryCode} />
                </FormControl>
                <FormControl id="population" isReadOnly mt={4}>
                  <FormLabel>Population</FormLabel>
                  <FormHelperText>
                    This field is automatically populated based on your selection.
                  </FormHelperText>
                  <Input name="population" value={formData.population} />
                </FormControl>
                <FormControl id="latitude" isReadOnly mt={4}>
                  <FormLabel>Latitude</FormLabel>
                  <FormHelperText>
                    This field is automatically populated based on your selection.
                  </FormHelperText>
                  <Input name="latitude" value={formData.latitude} />
                </FormControl>
                <FormControl id="longitude" isReadOnly mt={4}>
                  <FormLabel>Longitude</FormLabel>
                  <FormHelperText>
                    This field is automatically populated based on your selection.
                  </FormHelperText>
                  <Input name="longitude" value={formData.longitude} />
                </FormControl>
              </CardBody>
            </Card>

            {/* Funding Agencies */}
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Funding Agencies</Heading>
              </CardHeader>
              <CardBody>
                <FormControl id="Program_funding_agency" mt={4}>
                  <FormLabel>Program Funding Agency</FormLabel>
                  <FormHelperText>
                    Enter the organization that provided program funding.
                  </FormHelperText>
                  <Input
                    name="Program_funding_agency"
                    value={formData.Program_funding_agency}
                    onChange={handleChange}
                  />
                </FormControl>
                <FormControl id="Research_funding_agency" mt={4}>
                  <FormLabel>Research Funding Agency</FormLabel>
                  <FormHelperText>
                    Enter the organization that provided research funding.
                  </FormHelperText>
                  <Input
                    name="Research_funding_agency"
                    value={formData.Research_funding_agency}
                    onChange={handleChange}
                  />
                </FormControl>
              </CardBody>
            </Card>

            <Box mt={6} textAlign="center">
              <Button colorScheme="blue" type="submit" isLoading={isSubmitting}>
                Submit
              </Button>
            </Box>
          </Box>
        </>
      )}
    </Box>
  );
};

export default TrialSubmissionForm;
