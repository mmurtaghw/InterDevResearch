import axios from "axios";

const apiClient = axios.create({
  baseURL: "https://interdev2.adaptcentre.ie/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;
