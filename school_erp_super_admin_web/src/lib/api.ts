import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import { useAuth } from "@/stores/auth";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "https://api.campus.jaikalki.in";

export const api: AxiosInstance = axios.create({
  baseURL,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

// ---- Request interceptor: attach bearer --------------------------------

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jaikalki.access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// ---- Response interceptor: auto-refresh on 401, hard-logout on failure ----

let refreshInFlight: Promise<string | null> | null = null;

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false;
  return url.includes("/v1/auth/login")
    || url.includes("/v1/auth/refresh")
    || url.includes("/v1/auth/logout");
}

function hardLogout(): void {
  try {
    useAuth.getState().clear();
  } catch {
    // store may not be initialised yet; localStorage clear is enough.
  }
  localStorage.removeItem("jaikalki.access_token");
  if (window.location.pathname !== "/login") {
    window.location.replace("/login");
  }
}

async function attemptRefresh(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refreshToken = useAuth.getState().tokens?.refresh_token;
    if (!refreshToken) return null;
    try {
      const res = await axios.post<{
        access_token: string;
        refresh_token: string;
        expires_in: number;
        token_type: string;
      }>(
        `${baseURL}/v1/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { "Content-Type": "application/json" } },
      );
      useAuth.getState().setTokens(res.data);
      return res.data.access_token;
    } catch {
      return null;
    } finally {
      setTimeout(() => {
        refreshInFlight = null;
      }, 0);
    }
  })();

  return refreshInFlight;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error?.response?.status;

    if (status !== 401 || !original || original._retried || isAuthEndpoint(original.url)) {
      return Promise.reject(error);
    }

    original._retried = true;
    const newAccessToken = await attemptRefresh();
    if (!newAccessToken) {
      hardLogout();
      return Promise.reject(error);
    }

    original.headers = original.headers ?? {};
    original.headers["Authorization"] = `Bearer ${newAccessToken}`;
    return api.request(original);
  },
);
