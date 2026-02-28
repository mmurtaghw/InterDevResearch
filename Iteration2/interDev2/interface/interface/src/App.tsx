// App.tsx

import React, { useState, useCallback, useEffect } from "react";
import { Grid, GridItem, Show } from "@chakra-ui/react";
import {
  Routes,
  Route,
  useParams,
  useNavigate,
  Navigate,
} from "react-router-dom"; // Import `Navigate`
import NavBar from "./components/NavBar";
import NavSideBar from "./components/NavSideBar";
import GameGrid from "./components/GameGrid";
import TrialDetail from "./components/TrialDetail";
import TrialSubmissionForm from "./components/TrialSubmissionForm";
import CollectionList from "./components/CollectionList";
import CollectionView, {
  Props as CollectionViewProps,
} from "./components/CollectionView";
import { Trial, TrialFilter } from "./types/trialTypes";
import { CollectionType } from "./types/collectionTypes";
import apiClient from "./services/api-client-trials";

function App() {
  const [typeFilter, setSelectedFilter] = useState<TrialFilter>(
    {} as TrialFilter
  );
  const [selectedTrial, setSelectedTrial] = useState<Trial>({} as Trial);

  // State to manage multiple collections
  const [collections, setCollections] = useState<CollectionType[]>([]);

  const resetFilter = useCallback(() => {
    setSelectedFilter({} as TrialFilter); // Reset the filter to initial state
  }, []);

  const navigate = useNavigate();

  const handleSelectTrial = (trial: Trial) => {
    setSelectedTrial(trial);
    navigate(`/trial/${encodeURIComponent(trial.Title)}`); // Navigate to the trial detail page using Title or unique ID
  };

  const refreshCollections = useCallback(async () => {
    try {
      const response = await apiClient.get<{ results: CollectionType[] }>(
        "/collections"
      );
      setCollections(response.data.results || []);
    } catch (error) {
      console.error("Failed to fetch collections:", error);
    }
  }, []);

  useEffect(() => {
    void refreshCollections();
  }, [refreshCollections]);

  // Function to add a trial to a collection
  const addToCollection = (trialId: string, collectionName: string) => {
    void (async () => {
      try {
        await apiClient.post("/collections/trials", { collectionName, trialId });
        await refreshCollections();
      } catch (error) {
        console.error("Failed to add trial to collection:", error);
        alert("Failed to add trial to collection.");
      }
    })();
  };

  // Function to remove a trial from a collection
  const removeFromCollection = (trialId: string, collectionName: string) => {
    void (async () => {
      try {
        await apiClient.delete("/collections/trials", {
          data: { collectionName, trialId },
        });
        await refreshCollections();
      } catch (error) {
        console.error("Failed to remove trial from collection:", error);
        alert("Failed to remove trial from collection.");
      }
    })();
  };

  // Function to check if a trial is in a collection
  const isTrialInCollection = (trialId: string, collectionName: string) => {
    const collection = collections.find((col) => col.name === collectionName);
    return collection ? collection.trialIds.includes(trialId) : false;
  };

  // Function to create a new collection
  const createCollection = (name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) return;

    void (async () => {
      try {
        await apiClient.post("/collections", { name: trimmedName });
        await refreshCollections();
      } catch (error) {
        console.error("Failed to create collection:", error);
        alert("Failed to create collection.");
      }
    })();
  };

  // Function to download a collection
    // Now accepts a second parameter for format ("turtle", "csv", or "json")
  const downloadCollection = async (
    collectionName: string,
    format: string
  ) => {
    const collection = collections.find((col) => col.name === collectionName);
    if (!collection || collection.trialIds.length === 0) {
      alert("No trials in the collection to download.");
      return;
    }

    const baseUrl =
      "https://interdev2.adaptcentre.ie/download_knowledge_graph_data";
    // Build query string with trialIds and the selected format
    const query = `trialIds=${collection.trialIds.join(
      "&trialIds="
    )}&format=${format}`;

    try {
      const response = await fetch(`${baseUrl}?${query}`);
      if (!response.ok) {
        throw new Error("Network response was not ok.");
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      // Set file extension based on format
      link.setAttribute(
        "download",
        `${collectionName}.${format === "csv" ? "csv" : format === "json" ? "json" : "ttl"}`
      );
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
      {/* Navigation Bar */}
      <GridItem area="nav">
        <NavBar resetSelectedFilter={resetFilter} />
      </GridItem>

      {/* Sidebar */}
      <Show above="lg">
        <GridItem area="aside">
          <NavSideBar
            typeFilter={typeFilter}
            setSelectedFilter={setSelectedFilter}
          />
        </GridItem>
      </Show>

      {/* Main Content */}
      <GridItem area="main">
        <Routes>
          <Route
            path="/"
            element={
              <GameGrid
                trialFilter={typeFilter}
                onSelectTrial={handleSelectTrial}
                onAddTrialToCollection={addToCollection}
                onRemoveTrialFromCollection={removeFromCollection}
                isTrialInCollection={isTrialInCollection}
                collections={collections}
              />
            }
          />
          <Route
            path="/trial/:projectName"
            element={
              selectedTrial ? (
                <TrialDetail
                  trial={selectedTrial}
                  collections={collections}
                  onAddTrialToCollection={addToCollection}
                  onCreateCollection={createCollection}
                />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route path="/submission" element={<TrialSubmissionForm />} />
          <Route
            path="/collections"
            element={
              <CollectionList
                collections={collections}
                onCreateCollection={createCollection}
                onSelectCollection={(name) => {
                  navigate(`/collection/${encodeURIComponent(name)}`);
                }}
              />
            }
          />
          <Route
            path="/collection/:collectionName"
            element={
              <CollectionRouteComponent
                collections={collections}
                onSelectTrial={handleSelectTrial}
                onAddTrialToCollection={addToCollection}
                onRemoveTrialFromCollection={removeFromCollection}
                isTrialInCollection={isTrialInCollection}
                trialFilter={typeFilter}
                downloadCollection={downloadCollection}
              />
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </GridItem>
    </Grid>
  );
}

// Helper component for route handling
function CollectionRouteComponent(
  props: Omit<CollectionViewProps, "collectionName">
) {
  const { collectionName } = useParams<{ collectionName: string }>();
  if (!collectionName) {
    return <Navigate to="/collections" replace />;
  }
  return <CollectionView collectionName={collectionName} {...props} />;
}

export default App;
