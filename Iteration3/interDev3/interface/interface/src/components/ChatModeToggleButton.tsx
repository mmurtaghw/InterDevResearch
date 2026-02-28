import React from "react";
import { Box, Button, Text } from "@chakra-ui/react";
import { ChatMode, useChatMode } from "../context/ChatModeContext";

const MODE_LABELS: Record<ChatMode, string> = {
  none: "Mode: No Chat",
  chat: "Mode: Chat Only",
  "chat-sources": "Mode: Chat + Sources",
};

const ChatModeToggleButton: React.FC = () => {
  const { chatMode, cycleChatMode, isToggleVisible } = useChatMode();

  if (!isToggleVisible) {
    return null;
  }

  return (
    <Box position="fixed" bottom={6} right={6} zIndex={1400}>
      <Button
        size="sm"
        colorScheme="blue"
        onClick={cycleChatMode}
        boxShadow="lg"
        aria-label="Toggle chat display mode"
      >
        <Text fontSize="sm" fontWeight="medium">
          {MODE_LABELS[chatMode]}
        </Text>
      </Button>
    </Box>
  );
};

export default ChatModeToggleButton;
