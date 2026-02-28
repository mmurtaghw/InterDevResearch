import apiClient from "./api-client-trials";

export type EventPayload = Record<string, unknown>;

export const logEvent = async (
  eventType: string,
  data: EventPayload = {}
) => {
  try {
    await apiClient.post("/log_event", {
      eventType,
      data,
    });
  } catch (error) {
    // Swallow logging errors to avoid interrupting the UX
    // eslint-disable-next-line no-console
    console.warn("Failed to log event", error);
  }
};

