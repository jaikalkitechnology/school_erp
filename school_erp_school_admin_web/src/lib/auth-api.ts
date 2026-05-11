import { api } from "./api";
import type { AuthUser } from "@/stores/auth";

export interface LoginPayload {
  identifier: string;
  password: string;
  subdomain?: string;
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
  const { data } = await api.post<LoginResponse>("/v1/auth/login", payload, { headers });
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
