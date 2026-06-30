import { api } from "./api";
import type { AuthUser } from "@/stores/auth";

export interface LoginPayload {
  identifier: string;
  password: string;
  subdomain?: string;
  // Tell the backend this is the admin web so the role × platform
  // gate can reject parent / student accounts with the canonical
  // "You are not authorized to access the Admin Panel." message.
  platform?: "admin_panel" | "mobile_app";
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface LoginResponse {
  user: AuthUser;
  tokens: TokenPair;
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  // Override X-Tenant-Subdomain for *this* call so login isn't dependent on
  // whatever was previously persisted in localStorage. The middleware reads
  // the header before the body; without this override a stale subdomain
  // from a prior failed attempt would 404 at the tenant lookup.
  const headers: Record<string, string> = {};
  if (payload.subdomain) headers["X-Tenant-Subdomain"] = payload.subdomain;
  const body: LoginPayload = { platform: "admin_panel", ...payload };
  const { data } = await api.post<LoginResponse>("/v1/auth/login", body, { headers });
  return data;
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/v1/auth/me");
  return data;
}

export async function logout(refreshToken?: string): Promise<void> {
  await api.post("/v1/auth/logout", { refresh_token: refreshToken });
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/v1/auth/refresh", { refresh_token: refreshToken });
  return data;
}
