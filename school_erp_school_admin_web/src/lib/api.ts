import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import { useAuth } from "@/stores/auth";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "https://api.campus.jaikalki.in";

export const api: AxiosInstance = axios.create({
  baseURL,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

// ---- Request interceptor: attach bearer + tenant subdomain ----------------

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

// ---- Response interceptor: auto-refresh on 401, hard-logout on failure ----

/**
 * Coalesce concurrent 401s: only one /auth/refresh request fires at a
 * time, and every other 401'd request waits for that refresh to resolve.
 */
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
  localStorage.removeItem("jaikalki.subdomain");
  // Bypass react-router so the redirect still works from outside React
  // (axios interceptor runs in a non-component context). `replace` avoids
  // a "back" trap to the page that just 401'd.
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
      // Use a bare axios call so we don't recurse through this interceptor.
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
      // Cleared after the queue drains so concurrent callers see the same
      // resolution; the next 401 starts a fresh refresh.
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

    // Only act on 401 from non-auth endpoints, and only retry once per call.
    if (status !== 401 || !original || original._retried || isAuthEndpoint(original.url)) {
      return Promise.reject(error);
    }

    original._retried = true;
    const newAccessToken = await attemptRefresh();
    if (!newAccessToken) {
      // Refresh failed (expired refresh token / server rejected) → bail to
      // the login screen and reject the original promise.
      hardLogout();
      return Promise.reject(error);
    }

    // Re-issue the original request with the freshly-minted access token.
    original.headers = original.headers ?? {};
    original.headers["Authorization"] = `Bearer ${newAccessToken}`;
    return api.request(original);
  },
);
