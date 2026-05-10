import axios, { type AxiosInstance } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

// Phase 2 will swap this for a JWT-aware request interceptor.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jaikalki.access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("jaikalki.access_token");
    }
    return Promise.reject(error);
  },
);
