import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import apiClient from "../services/api-client-trials";
import { useParticipant } from "./ParticipantContext";

export type ChatMode = "none" | "chat" | "chat-sources";

const CHAT_MODE_SEQUENCE: ChatMode[] = ["none", "chat", "chat-sources"];

interface ChatModeContextValue {
  chatMode: ChatMode;
  setChatMode: (mode: ChatMode) => void;
  cycleChatMode: () => void;
  isToggleVisible: boolean;
}

const ChatModeContext = createContext<ChatModeContextValue | undefined>(
  undefined
);

export const ChatModeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { participantName } = useParticipant();
  const [chatMode, setChatModeState] = useState<ChatMode>("none");
  const [isToggleVisible] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchCondition = async () => {
      if (!participantName) {
        setChatModeState("none");
        return;
      }
      try {
        const response = await apiClient.get("/participant_condition");
        const assignedMode = response.data?.chatMode as ChatMode | undefined;
        if (!isMounted) {
          return;
        }
        if (assignedMode && CHAT_MODE_SEQUENCE.includes(assignedMode)) {
          setChatModeState(assignedMode);
        } else {
          setChatModeState("none");
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }
        console.warn("Failed to fetch participant condition", error);
        setChatModeState("none");
      }
    };
    fetchCondition();
    return () => {
      isMounted = false;
    };
  }, [participantName]);

  const setChatMode = useCallback((mode: ChatMode) => {
    // Explicit mode changes are disabled in study mode; this setter is a no-op.
    if (!CHAT_MODE_SEQUENCE.includes(mode)) {
      return;
    }
  }, []);

  const cycleChatMode = useCallback(() => {
    // Mode cycling is disabled; conditions are assigned server-side per participant.
  }, []);

  const value = useMemo<ChatModeContextValue>(
    () => ({
      chatMode,
      setChatMode,
      cycleChatMode,
      isToggleVisible,
    }),
    [chatMode, setChatMode, cycleChatMode, isToggleVisible]
  );

  return (
    <ChatModeContext.Provider value={value}>{children}</ChatModeContext.Provider>
  );
};

export const useChatMode = () => {
  const context = useContext(ChatModeContext);
  if (!context) {
    throw new Error("useChatMode must be used within a ChatModeProvider");
  }
  return context;
};
