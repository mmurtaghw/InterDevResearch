import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider } from "@chakra-ui/react";
import App from "./App";
import theme from "./theme";
import "./index.css";
import { BrowserRouter } from "react-router-dom";
import { ChatModeProvider } from "./context/ChatModeContext";
import { ParticipantProvider } from "./context/ParticipantContext";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <BrowserRouter>
        <ParticipantProvider>
          <ChatModeProvider>
            <App />
          </ChatModeProvider>
        </ParticipantProvider>
      </BrowserRouter>
    </ChakraProvider>
  </React.StrictMode>
);
