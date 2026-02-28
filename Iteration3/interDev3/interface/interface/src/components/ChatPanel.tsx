import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  HStack,
  Input,
  Spinner,
  Text,
  VStack,
  Heading,
  Link,
  OrderedList,
  ListItem,
} from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import apiClient, { buildApiUrl } from "../services/api-client-trials";
import { logEvent } from "../services/eventLogger";
import { useChatMode } from "../context/ChatModeContext";

type ChatSource = {
  id?: string;
  trialId?: string;
  trialTitle?: string;
  trialCurie?: string;
  sourceTitle?: string;
  sourceUrl?: string;
  doi?: string;
  authors?: string;
  excerpt?: string;
  href?: string;
  kgHref?: string;
  sectors?: string[];
  countries?: string[];
  funders?: string[];
  methods?: string[];
  outcomes?: string[];
};

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: ChatSource[];
};

interface ChatPanelProps {
  trialIds?: string[];
  title?: string;
  showSources?: boolean;
  collectionName?: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  trialIds = [],
  title,
  showSources = true,
  collectionName,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "system",
      content:
        "You are an assistant helping users explore RCTs in this collection.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
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

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading, error]);

  const buildKgDownloadLink = (trialCurie?: string) => {
    if (!trialCurie) return undefined;
    const trialIdParam =
      trialCurie.includes(":") ? trialCurie.split(":").pop() : trialCurie;
    if (!trialIdParam) return undefined;
    return `${buildApiUrl(
      "/download_knowledge_graph_data"
    )}?trialIds=${encodeURIComponent(trialIdParam)}&format=turtle`;
  };

  const formatSources = (sources: ChatSource[] = []) =>
    sources.map((source) => {
      if (source.href) {
        return source;
      }
      const rawUrl = source.sourceUrl?.trim() || "";
      const rawDoi = source.doi?.trim() || "";
      const doiNoPrefix = rawDoi.replace(/^doi:/i, "").trim();
      const doiUrl = rawDoi && rawDoi.toLowerCase().startsWith("http")
        ? rawDoi
        : doiNoPrefix
        ? `https://doi.org/${doiNoPrefix.replace(/^\/+/, "")}`
        : "";
      const kgHref = buildKgDownloadLink(source.trialCurie || source.trialId);
      const href = rawUrl || doiUrl || kgHref || undefined;
      return { ...source, href, kgHref };
    });

  const logSourceClick = useCallback(
    (
      origin: "markdown" | "source" | "kg",
      info: Record<string, unknown>
    ) => {
      if (!collectionName) {
        return;
      }
      recordEvent("chat_source_click", {
        origin,
        collectionName,
        ...info,
      });
    },
    [collectionName, recordEvent]
  );

  const markdownComponents = useMemo(
    () => ({
      a: ({ href, children, ...props }: any) => {
        const linkHref = href || "#";
        const text = React.Children.toArray(children)
          .map((child) => {
            if (typeof child === "string") {
              return child;
            }
            if (React.isValidElement(child)) {
              const childChildren = React.Children.toArray(
                child.props.children
              ).join("");
              return childChildren;
            }
            return "";
          })
          .join("");
        return (
          <Link
            {...props}
            href={linkHref}
            isExternal
            color="blue.600"
            onClick={(event) => {
              props.onClick?.(event);
              if (event.defaultPrevented) {
                return;
              }
              if (linkHref) {
                logSourceClick("markdown", {
                  href: linkHref,
                  text,
                });
              }
            }}
          >
            {children}
          </Link>
        );
      },
    }),
    [logSourceClick]
  );

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setError(null);
    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: trimmed } as ChatMessage,
    ];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    try {
      const resp = await apiClient.post("/chat", {
        messages: nextMessages,
        trialIds,
      });
      const reply: string = resp.data?.reply || "";
      const sources: ChatSource[] = formatSources(resp.data?.sources || []);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply, sources } as ChatMessage,
      ]);
    } catch (e: any) {
      setError(e?.response?.data?.error || "Failed to get reply");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} mt={4}>
      <Heading as="h3" size="md" mb={3}>
        {title || "Ask about this collection"}
      </Heading>
      <VStack
        ref={scrollContainerRef}
        align="stretch"
        spacing={3}
        maxH="320px"
        overflowY="auto"
        mb={3}
      >
        {messages
          .filter((m) => m.role !== "system")
          .map((m, idx) => {
            const allSources = formatSources(m.sources || []);
            const sourceHrefMap = new Map<string, string>();
            allSources.forEach((source, sourceIdx) => {
              if (source.href) {
                sourceHrefMap.set(`S${sourceIdx + 1}`, source.href);
              }
            });

            let contentWithLinks = m.content;
            if (m.role === "assistant") {
              if (showSources && sourceHrefMap.size > 0) {
                contentWithLinks = m.content.replace(/\[S(\d+)\]/g, (match, num) => {
                  const key = `S${num}`;
                  const target = sourceHrefMap.get(key);
                  return target ? `[${key}](${target})` : match;
                });
              } else if (!showSources) {
                contentWithLinks = m.content.replace(/\[S(\d+)\]/g, "");
              }
            }

            const visibleSources = showSources ? allSources : [];

            return (
              <Box
                key={idx}
                bg={m.role === "user" ? "blue.50" : "gray.50"}
                borderRadius="md"
                p={2}
              >
                <Text fontSize="sm" color="gray.600">
                  {m.role === "user" ? "You" : "Assistant"}
                </Text>
                <Box
                  fontSize="sm"
                  color="gray.800"
                  sx={{
                    "& p": { marginBottom: 2 },
                    "& ul": { paddingLeft: "1.25rem", marginBottom: 2 },
                    "& ol": { paddingLeft: "1.25rem", marginBottom: 2 },
                    "& li": { marginBottom: 1 },
                    "& strong": { fontWeight: "semibold" },
                  }}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {contentWithLinks}
                  </ReactMarkdown>
                </Box>
                {m.role === "assistant" && visibleSources.length > 0 && (
                  <Box mt={2}>
                    <Text fontSize="xs" color="gray.500">
                      Sources
                    </Text>
                    <OrderedList spacing={1} pl={4} fontSize="xs" color="gray.600">
                      {visibleSources.map((source, sourceIdx) => {
                        const label = source.sourceTitle?.trim() || source.trialTitle?.trim() || "Source";
                        const href = source.href;
                        const excerpt = source.excerpt?.trim();
                        const excerptSnippet = excerpt && excerpt.length > 240 ? `${excerpt.slice(0, 240)}…` : excerpt;
                        const kgLink = buildKgDownloadLink(source.trialCurie || source.trialId);
                        return (
                          <ListItem key={`${idx}-src-${sourceIdx}`}>
                            <Box>
                              {href ? (
                                <Link
                                  href={href}
                                  isExternal
                                  color="blue.600"
                                  onClick={() =>
                                    logSourceClick("source", {
                                      href,
                                      label,
                                      messageIndex: idx,
                                      sourceIndex: sourceIdx + 1,
                                      trialCurie:
                                        source.trialCurie || source.trialId,
                                    })
                                  }
                                >
                                  {label}
                                </Link>
                              ) : (
                                <Text as="span" color="gray.700">
                                  {label}
                                </Text>
                              )}
                              {source.trialTitle && source.trialTitle !== label && (
                                <Text as="span" color="gray.500">
                                  {` — ${source.trialTitle}`}
                                </Text>
                              )}
                            </Box>
                            {excerptSnippet && (
                              <Text mt={1} fontSize="xs" color="gray.500">
                                {excerptSnippet}
                              </Text>
                            )}
                            <VStack align="stretch" spacing={0} mt={1}>
                              {(source.trialCurie || kgLink) && (
                                <Text fontSize="xs" color="gray.500">
                                  KG ID:{" "}
                                  {kgLink ? (
                                    <Link
                                      href={kgLink}
                                      isExternal
                                      color="blue.600"
                                      onClick={() =>
                                        logSourceClick("kg", {
                                          href: kgLink,
                                          label,
                                          messageIndex: idx,
                                          sourceIndex: sourceIdx + 1,
                                          trialCurie:
                                            source.trialCurie || source.trialId,
                                        })
                                      }
                                    >
                                      {source.trialCurie || source.trialId}
                                    </Link>
                                  ) : (
                                    source.trialCurie || source.trialId
                                  )}
                                </Text>
                              )}
                              {source.sectors && source.sectors.length > 0 && (
                                <Text fontSize="xs" color="gray.500">
                                  Sector: {source.sectors.join(", ")}
                                </Text>
                              )}
                              {source.countries && source.countries.length > 0 && (
                                <Text fontSize="xs" color="gray.500">
                                  Countries: {source.countries.join(", ")}
                                </Text>
                              )}
                              {source.methods && source.methods.length > 0 && (
                                <Text fontSize="xs" color="gray.500">
                                  Methods: {source.methods.join(", ")}
                                </Text>
                              )}
                              {source.outcomes && source.outcomes.length > 0 && (
                                <Text fontSize="xs" color="gray.500">
                                  Outcomes: {source.outcomes.join(", ")}
                                </Text>
                              )}
                              {source.funders && source.funders.length > 0 && (
                                <Text fontSize="xs" color="gray.500">
                                  Funders: {source.funders.join(", ")}
                                </Text>
                              )}
                            </VStack>
                          </ListItem>
                        );
                      })}
                    </OrderedList>
                  </Box>
                )}
              </Box>
            );
          })}
        {loading && (
          <HStack>
            <Spinner size="sm" />
            <Text>Thinking…</Text>
          </HStack>
        )}
        {error && (
          <Text color="red.500" fontSize="sm">
            {error}
          </Text>
        )}
      </VStack>
      <HStack>
        <Input
          value={input}
          placeholder="Ask about the trials in this collection…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
        />
        <Button colorScheme="blue" onClick={sendMessage} isDisabled={loading}>
          Send
        </Button>
      </HStack>
    </Box>
  );
};

export default ChatPanel;
