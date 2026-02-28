import axios from "axios";

// Prefer env override when provided, otherwise use Vite proxy path
const apiBase = import.meta.env?.VITE_API_BASE_URL || "/api";

const apiClient = axios.create({
  baseURL: apiBase,
  headers: {
    "Content-Type": "application/json",
  },
});

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const base = ((apiClient.defaults.baseURL as string | undefined) || "").replace(
    /\/+$/,
    ""
  );
  if (!base || base === "/") {
    return normalizedPath;
  }
  return `${base}${normalizedPath}`;
};

export const setParticipantIdentity = (name: string | null) => {
  if (name && name.trim()) {
    const trimmed = name.trim();
    apiClient.defaults.headers.common["X-Participant-Name"] = trimmed;
  } else {
    delete apiClient.defaults.headers.common["X-Participant-Name"];
  }
};

export default apiClient;
