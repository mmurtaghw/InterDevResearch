import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { setParticipantIdentity } from "../services/api-client-trials";

type ParticipantContextType = {
  participantName: string | null;
  setParticipantName: (name: string) => void;
  clearParticipant: () => void;
};

const ParticipantContext = createContext<ParticipantContextType | undefined>(
  undefined
);

const STORAGE_KEY = "participantName";

export const ParticipantProvider: React.FC<React.PropsWithChildren> = ({
  children,
}) => {
  const [participantName, setParticipantNameState] = useState<string | null>(
    () => {
      if (typeof window === "undefined") {
        return null;
      }
      const stored = window.localStorage.getItem(STORAGE_KEY);
      return stored ? stored : null;
    }
  );

  const setParticipantName = useCallback((name: string) => {
    setParticipantNameState(name);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, name);
    }
    setParticipantIdentity(name);
  }, []);

  const clearParticipant = useCallback(() => {
    setParticipantNameState(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
    setParticipantIdentity(null);
  }, []);

  useEffect(() => {
    if (participantName) {
      setParticipantIdentity(participantName);
    } else {
      setParticipantIdentity(null);
    }
  }, [participantName]);

  const value = useMemo(
    () => ({ participantName, setParticipantName, clearParticipant }),
    [participantName, setParticipantName, clearParticipant]
  );

  return (
    <ParticipantContext.Provider value={value}>
      {children}
    </ParticipantContext.Provider>
  );
};

export const useParticipant = (): ParticipantContextType => {
  const context = useContext(ParticipantContext);
  if (!context) {
    throw new Error("useParticipant must be used within a ParticipantProvider");
  }
  return context;
};
