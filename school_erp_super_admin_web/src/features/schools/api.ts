import { api } from "@/lib/api";
import type { CreateTenantPayload, SubscriptionPlan, Tenant } from "./types";

export async function listTenants(search?: string): Promise<Tenant[]> {
  const { data } = await api.get<Tenant[]>("/admin/tenants", { params: search ? { search } : undefined });
  return data;
}

export async function createTenant(payload: CreateTenantPayload): Promise<Tenant> {
  const { data } = await api.post<Tenant>("/admin/tenants", payload);
  return data;
}

export async function suspendTenant(id: number): Promise<Tenant> {
  const { data } = await api.post<Tenant>(`/admin/tenants/${id}/suspend`);
  return data;
}

export async function activateTenant(id: number): Promise<Tenant> {
  const { data } = await api.post<Tenant>(`/admin/tenants/${id}/activate`);
  return data;
}

export interface TenantHealth {
  tenant_id: number;
  subdomain: string;
  status: string;
  storage_used_mb: number;
  storage_limit_mb: number;
  storage_used_pct: number;
  student_limit: number;
  teacher_limit: number;
}

export async function tenantHealth(id: number): Promise<TenantHealth> {
  const { data } = await api.get<TenantHealth>(`/admin/tenants/${id}/health`);
  return data;
}

export async function listPlans(): Promise<SubscriptionPlan[]> {
  const { data } = await api.get<SubscriptionPlan[]>("/admin/plans");
  return data;
}
