import { Button, Grid, GridItem, VStack } from "@chakra-ui/react";
import NavBar from "./components/NavBar";
import GameGrid from "./components/GameGrid";
import { useState, useCallback } from "react";
import { Trial, TrialFilter } from "./hooks/useTrials";
import { Route, Routes } from "react-router-dom";
import TrialDetail from "./components/TrialDetail";
import NavSideBar from "./components/NavSideBar";
import TrialSubmissionForm from "./components/TrialSubmissionForm";
import Collection from "./components/Collection";
import AddCollectionButton from "./components/AddCollectionButton";
import apiClient from "./services/api-client-trials";
import qs from "qs";

function App() {
  const [typeFilter, setSelectedFilter] = useState<TrialFilter>(
    {} as TrialFilter
  );
  const [selectedTrial, setSelectedTrial] = useState<Trial>({} as Trial);
  const [trialCollection, setTrialCollection] = useState<string[]>([]);
  const isTrialInCollection = (trialId: string) => {
    return trialCollection.includes(trialId);
  };
  const resetFilter = useCallback(() => {
    setSelectedFilter({} as TrialFilter); // Reset the filter to initial state
  }, []);

  const addToCollection = (trialId: string) => {
    setTrialCollection((prevCollection) => {
      // Check if the trialId is already in the collection
      if (!prevCollection.includes(trialId)) {
        return [...prevCollection, trialId];
      }
      return prevCollection;
    });
  };
  const removeFromCollection = (trialId: string) => {
    setTrialCollection((prevCollection) => {
      // Remove the trialId from the collection
      return prevCollection.filter((id) => id !== trialId);
    });
  };

  const downloadCollection = async () => {
    if (trialCollection.length === 0) {
      alert("No trials in the collection to download.");
      return;
    }

    try {
      const response = await apiClient.get("/download_knowledge_graph_data", {
        params: { trialIds: trialCollection },
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: "repeat" }),
        responseType: "blob",
      });

      const blob = response.data;
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", "collection.ttl");
      document.body.appendChild(link);
      link.click();

      if (link.parentNode) {
        link.parentNode.removeChild(link);
      }

      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error("Failed to download the collection:", error);
      alert("Failed to download the collection. Please try again.");
    }
  };

  return (
    <Grid
      templateAreas={{
        base: `"nav" "main"`,
        lg: `"nav nav" "aside main"`,
      }}
      templateColumns={{
        base: "1fr",
        lg: "200px 1fr",
      }}
    >
      <GridItem area="nav">
        {" "}
        <NavBar resetSelectedFilter={resetFilter}></NavBar>
      </GridItem>
      <Routes>
        <Route
          path="/"
          element={
            <NavSideBar
              typeFilter={typeFilter}
              setSelectedFilter={setSelectedFilter}
            ></NavSideBar>
          }
        />
        <Route
          path="/collection"
          element={
            <VStack spacing={4} align="stretch">
              <Button
                colorScheme="green"
                size="md"
                marginLeft={4}
                marginRight={4}
                onClick={downloadCollection}
              >
                Download Collection
              </Button>

              <NavSideBar
                typeFilter={typeFilter}
                setSelectedFilter={setSelectedFilter}
              />
            </VStack>
          }
        />
        <Route
          path="/trial/:projectName"
          element={
            <VStack spacing={4} align="stretch">
              <AddCollectionButton
                trial={selectedTrial}
                onAddTrialToCollection={addToCollection}
                onRemoveTrialFromCollection={removeFromCollection}
                isInCollection={isTrialInCollection}
                buttonProps={{
                  size: "md",
                  marginLeft: 4,
                  marginRight: 4,
                  whiteSpace: "normal",
                }}
              />
            </VStack>
          }
        />
      </Routes>
      <GridItem area="main">
        <Routes>
          <Route
            path="/"
            element={
              <GameGrid
                trialFilter={typeFilter}
                onSelectTrial={setSelectedTrial}
                isInCollection={isTrialInCollection}
                onAddTrialToCollection={addToCollection}
                onRemoveTrialFromCollection={removeFromCollection}
              />
            }
          />
          {/* Dynamic route for trials */}
          <Route
            path="/trial/:projectName"
            element={<TrialDetail trial={selectedTrial} />}
          />
          <Route
            path="/submission"
            element={
              <>
                <TrialSubmissionForm></TrialSubmissionForm>
              </>
            } // A component to display trial details
          />
          <Route
            path="/collection"
            element={
              <>
                <Collection
                  onSelectTrial={setSelectedTrial}
                  trialFilter={typeFilter}
                  trialIds={trialCollection}
                  isInCollection={isTrialInCollection}
                  onAddTrialToCollection={addToCollection}
                  onRemoveTrialFromCollection={removeFromCollection}
                ></Collection>
              </>
            } // A component to display trial details
          />
        </Routes>
      </GridItem>
    </Grid>
  );
}

export default App;
