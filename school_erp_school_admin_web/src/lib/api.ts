import axios, { type AxiosInstance } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "https://api.campus.jaikalki.in";

export const api: AxiosInstance = axios.create({
  baseURL,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jaikalki.access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  // School admin web is tenant-scoped: forward the subdomain so the FastAPI
  // tenant middleware can resolve the right school during local dev where
  // the request hits localhost:8000 without a real subdomain. An explicit
  // per-call override (e.g. login) takes precedence over the stored value.
  config.headers = config.headers ?? {};
  if (!config.headers["X-Tenant-Subdomain"]) {
    const subdomain = localStorage.getItem("jaikalki.subdomain");
    if (subdomain) {
      config.headers["X-Tenant-Subdomain"] = subdomain;
    }
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
