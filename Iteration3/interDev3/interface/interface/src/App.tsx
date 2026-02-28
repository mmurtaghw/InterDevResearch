// App.tsx

import React, {
  useState,
  useCallback,
  useEffect,
  useRef,
  useMemo,
} from "react";
import {
  Grid,
  GridItem,
  VStack,
  Show,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  FormControl,
  FormLabel,
  Input,
  Text,
} from "@chakra-ui/react";
import {
  Routes,
  Route,
  useParams,
  useNavigate,
  useLocation,
  Navigate,
} from "react-router-dom"; // Import `Navigate`
import NavBar from "./components/NavBar";
import NavSideBar from "./components/NavSideBar";
import ActiveFiltersBar from "./components/ActiveFiltersBar";
import GameGrid from "./components/GameGrid";
import TrialDetail from "./components/TrialDetail";
import TrialSubmissionForm from "./components/TrialSubmissionForm";
import CollectionList from "./components/CollectionList";
import CollectionView, {
  Props as CollectionViewProps,
} from "./components/CollectionView";
import { Trial, TrialFilter } from "./types/trialTypes";
import { CollectionType } from "./types/collectionTypes";
import { useParticipant } from "./context/ParticipantContext";
import { logEvent } from "./services/eventLogger";
import { useChatMode } from "./context/ChatModeContext";
import { getName as getCountryName } from "country-list";
import apiClient, { buildApiUrl } from "./services/api-client-trials";

type FilterKey = keyof TrialFilter | "search";

const FILTER_FIELDS: { key: keyof TrialFilter; label: string }[] = [
  { key: "Sector", label: "Sector" },
  { key: "Sub_sector", label: "Sub-sector" },
  { key: "Evaluation_design", label: "Evaluation Design" },
  { key: "Equity_focus", label: "Equity Focus" },
  { key: "Program_funding_agency", label: "Program Funding Agency" },
  { key: "Implementation_agency", label: "Implementation Agency" },
  { key: "countryCode", label: "Country" },
];

function App() {
  const [typeFilter, setSelectedFilter] = useState<TrialFilter>(
    {} as TrialFilter
  );
  const [searchText, setSearchText] = useState<string>("");
  const [selectedTrial, setSelectedTrial] = useState<Trial>({} as Trial);

  // State to manage multiple collections
  const [collections, setCollections] = useState<CollectionType[]>([]);
  const { participantName, setParticipantName, clearParticipant } =
    useParticipant();
  const [nameInput, setNameInput] = useState<string>(participantName ?? "");
  const detailSessionRef = useRef<{
    startTime: number;
    trialId: string;
    trialTitle: string;
    source: "evidence" | "collection";
    collectionName?: string;
  } | null>(null);
  const detailRequestRef = useRef<number | null>(null);
  const lastCollectionEventRef = useRef<{
    signature: string;
    time: number;
  } | null>(null);
  const hasLoggedLoginRef = useRef(false);

  const location = useLocation();
  const { chatMode } = useChatMode();
  const conditionLabel = useMemo(() => {
    switch (chatMode) {
      case "none":
        return "no chat";
      case "chat":
        return "chat";
      case "chat-sources":
      default:
        return "chat + sources";
    }
  }, [chatMode]);
  const recordEvent = useCallback(
    (eventType: string, data: Record<string, unknown> = {}) => {
      logEvent(eventType, { condition: conditionLabel, ...data });
    },
    [conditionLabel]
  );
  const activeFilterChips = useMemo(() => {
    const chips: { key: FilterKey; label: string; value: string }[] = [];
    const trimmedSearch = searchText.trim();
    if (trimmedSearch) {
      chips.push({ key: "search", label: "Search", value: trimmedSearch });
    }
    FILTER_FIELDS.forEach(({ key, label }) => {
      const raw = typeFilter[key];
      if (!raw) return;
      const values = Array.isArray(raw) ? raw : [raw];
      values.forEach((value) => {
        if (!value) return;
        let displayValue = String(value);
        if (key === "countryCode") {
          const countryName = getCountryName(displayValue.toUpperCase());
          if (countryName) {
            displayValue = countryName;
          }
        }
        chips.push({ key, label, value: displayValue });
      });
    });
    return chips;
  }, [searchText, typeFilter]);

  const handleClearFilter = useCallback(
    (key: FilterKey) => {
      if (key === "search") {
        if (searchText) {
          recordEvent("filter_removed", { key: "search", value: searchText });
        }
        setSearchText("");
        setSelectedFilter((prev) => {
          const next = { ...prev } as Record<string, unknown>;
          delete next.search;
          return next as TrialFilter;
        });
        return;
      }

      const currentValue = typeFilter[key];
      if (currentValue) {
        const valueText = Array.isArray(currentValue)
          ? currentValue.join(", ")
          : currentValue;
        recordEvent("filter_removed", { key, value: valueText });
      } else {
        recordEvent("filter_removed", { key });
      }

      setSelectedFilter((prev) => {
        const next = { ...prev } as Record<string, unknown>;
        delete next[key as keyof TrialFilter];
        return next as TrialFilter;
      });
    },
    [recordEvent, searchText, setSearchText, setSelectedFilter, typeFilter]
  );

  useEffect(() => {
    setNameInput(participantName ?? "");
    if (participantName && !hasLoggedLoginRef.current) {
      recordEvent("session_login", {
        participantName,
        source: "resume",
      });
      hasLoggedLoginRef.current = true;
    }
  }, [participantName, recordEvent]);

  const fetchCollections = useCallback(async () => {
    if (!participantName) {
      setCollections([]);
      return;
    }
    try {
      const response = await apiClient.get<{ results: CollectionType[] }>(
        "/collections"
      );
      setCollections(response.data?.results || []);
    } catch (error) {
      console.error("Failed to fetch collections", error);
      setCollections([]);
    }
  }, [participantName]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const closeDetailSession = useCallback(
    (reason: "navigate" | "switch" | "unmount") => {
      const session = detailSessionRef.current;
      if (!session) {
        return;
      }
      const durationMs = Date.now() - session.startTime;
      recordEvent("detail_view_close", {
        reason,
        trialId: session.trialId,
        trialTitle: session.trialTitle,
        source: session.source,
        collectionName: session.collectionName,
        durationMs,
      });
      detailSessionRef.current = null;
      detailRequestRef.current = null;
    },
    [recordEvent]
  );

  const emitCollectionEvent = useCallback(
    (payload: Record<string, unknown>) => {
      const signature = JSON.stringify(payload);
      const now = Date.now();
      const last = lastCollectionEventRef.current;
      if (last && last.signature === signature && now - last.time < 10) {
        return;
      }
      lastCollectionEventRef.current = { signature, time: now };
      recordEvent("collection_update", payload);
    },
    [recordEvent]
  );

  const handleParticipantSubmit = useCallback(() => {
    const trimmed = nameInput.trim();
    if (!trimmed) {
      return;
    }
    setParticipantName(trimmed);
    recordEvent("session_login", {
      participantName: trimmed,
      source: "manual",
    });
    hasLoggedLoginRef.current = true;
  }, [nameInput, recordEvent, setParticipantName]);

  const handleSearchSubmit = useCallback(
    (query: string) => {
      const trimmedQuery = (query || "").trim();
      setSearchText(trimmedQuery);
      setSelectedFilter((prevFilter) => {
        const nextFilter: TrialFilter = { ...prevFilter };
        if (trimmedQuery) {
          nextFilter.search = trimmedQuery;
        } else {
          delete nextFilter.search;
        }
        return nextFilter;
      });
    },
    [setSelectedFilter]
  );

  useEffect(() => {
    if (!location.pathname.startsWith("/trial/")) {
      closeDetailSession("navigate");
    }
  }, [location.pathname, closeDetailSession]);

  useEffect(() => () => {
    closeDetailSession("unmount");
  }, [closeDetailSession]);

  const navigate = useNavigate();
  const fetchTrialDetails = useCallback(async (trialId: string): Promise<Trial | null> => {
    try {
      const response = await apiClient.get<{ results: Trial[] }>(
        "/knowledge_graph_data",
        {
          params: { trialIds: trialId, limit: 1, view: "detail" },
        }
      );
      return response.data?.results?.[0] ?? null;
    } catch (error) {
      console.error("Failed to fetch trial details", error);
      return null;
    }
  }, []);

  const handleSelectTrial = useCallback(
    (
      trial: Trial,
      context?: { source: "evidence" | "collection"; collectionName?: string }
    ) => {
      closeDetailSession("switch");
      setSelectedTrial(trial);
      const source = context?.source ?? (context?.collectionName ? "collection" : "evidence");
      detailSessionRef.current = {
        startTime: Date.now(),
        trialId: trial.id,
        trialTitle: trial.Title,
        source,
        collectionName: context?.collectionName,
      };
      recordEvent("detail_view_open", {
        trialId: trial.id,
        trialTitle: trial.Title,
        source,
        collectionName: context?.collectionName,
      });
      navigate(`/trial/${encodeURIComponent(trial.Title)}`);
      const requestId = Date.now();
      detailRequestRef.current = requestId;
      fetchTrialDetails(trial.id).then((fullTrial) => {
        if (!fullTrial) {
          return;
        }
        if (detailRequestRef.current !== requestId) {
          return;
        }
        setSelectedTrial(fullTrial);
      });
    },
    [closeDetailSession, navigate, recordEvent, fetchTrialDetails]
  );

  const handleLogout = useCallback(() => {
    closeDetailSession("switch");
    if (participantName) {
      recordEvent("session_logout", { participantName });
    } else {
      recordEvent("session_logout");
    }
    clearParticipant();
    hasLoggedLoginRef.current = false;
    setSelectedTrial({} as Trial);
  }, [clearParticipant, closeDetailSession, participantName, recordEvent]);

  const upsertCollectionInState = useCallback((collection: CollectionType) => {
    setCollections((prevCollections) => {
      const index = prevCollections.findIndex((col) => col.name === collection.name);
      if (index === -1) {
        return [...prevCollections, collection];
      }
      const nextCollections = [...prevCollections];
      nextCollections[index] = collection;
      return nextCollections;
    });
  }, []);

  // Function to add a trial to a collection
  const addToCollection = async (trialId: string, collectionName: string) => {
    const trimmedName = collectionName.trim();
    if (!trimmedName) {
      return;
    }
    try {
      const response = await apiClient.post<{ collection: CollectionType }>(
        `/collections/${encodeURIComponent(trimmedName)}/trials`,
        { trialId }
      );
      const updatedCollection = response.data?.collection;
      if (updatedCollection) {
        upsertCollectionInState(updatedCollection);
        emitCollectionEvent({
          action: "add_trial",
          collectionName: updatedCollection.name,
          trialId,
          size: updatedCollection.trialIds.length,
          trialIds: updatedCollection.trialIds,
        });
      }
    } catch (error) {
      console.error("Failed to add trial to collection", error);
    }
  };

  // Function to remove a trial from a collection
  const removeFromCollection = async (trialId: string, collectionName: string) => {
    const trimmedName = collectionName.trim();
    if (!trimmedName) {
      return;
    }
    try {
      const response = await apiClient.delete<{ collection: CollectionType }>(
        `/collections/${encodeURIComponent(trimmedName)}/trials/${encodeURIComponent(
          trialId
        )}`
      );
      const updatedCollection = response.data?.collection;
      if (updatedCollection) {
        upsertCollectionInState(updatedCollection);
        emitCollectionEvent({
          action: "remove_trial",
          collectionName: updatedCollection.name,
          trialId,
          size: updatedCollection.trialIds.length,
          trialIds: updatedCollection.trialIds,
        });
      }
    } catch (error) {
      console.error("Failed to remove trial from collection", error);
    }
  };

  // Function to check if a trial is in a collection
  const isTrialInCollection = (trialId: string, collectionName: string) => {
    const collection = collections.find((col) => col.name === collectionName);
    return collection ? collection.trialIds.includes(trialId) : false;
  };

  // Function to create a new collection
  const createCollection = async (name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      return;
    }
    try {
      const response = await apiClient.post<{ collection: CollectionType }>(
        "/collections",
        { name: trimmedName }
      );
      const createdCollection = response.data?.collection;
      if (createdCollection) {
        upsertCollectionInState(createdCollection);
        emitCollectionEvent({
          action: "create",
          collectionName: createdCollection.name,
          size: createdCollection.trialIds.length,
          trialIds: createdCollection.trialIds,
        });
      }
    } catch (error) {
      console.error("Failed to create collection", error);
    }
  };

  // Function to download a collection
  // Now accepts a second parameter for format (either "turtle" or "csv")
  const downloadCollection = async (
    collectionName: string,
    format: string
  ) => {
    const collection = collections.find((col) => col.name === collectionName);
    if (!collection || collection.trialIds.length === 0) {
      alert("No trials in the collection to download.");
      return;
    }

    const baseUrl = buildApiUrl("/download_knowledge_graph_data");
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
        `${collectionName}.${format === "csv" ? "csv" : "ttl"}`
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
    <>
      <Modal
        isOpen={!participantName}
        onClose={() => {}}
        closeOnEsc={false}
        closeOnOverlayClick={false}
        isCentered
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Enter Participant Name</ModalHeader>
          <ModalBody>
            <Text mb={4}>
              Please provide your name or study ID before continuing.
            </Text>
            <FormControl>
              <FormLabel srOnly>Participant Name</FormLabel>
              <Input
                value={nameInput}
                onChange={(event) => setNameInput(event.target.value)}
                placeholder="Enter your name"
                autoFocus
              />
            </FormControl>
          </ModalBody>
          <ModalFooter>
            <Button
              colorScheme="blue"
              onClick={handleParticipantSubmit}
              isDisabled={!nameInput.trim()}
            >
              Continue
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
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
        <NavBar
          searchQuery={searchText}
          onSearchSubmit={handleSearchSubmit}
          onLogout={handleLogout}
        />
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
        <ActiveFiltersBar
          filters={activeFilterChips.map((chip) => ({
            key: chip.key,
            label: chip.label,
            value: chip.value,
          }))}
          onClear={(key) => handleClearFilter(key as FilterKey)}
        />
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
                selectContext={{ source: "evidence" }}
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
    </>
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
