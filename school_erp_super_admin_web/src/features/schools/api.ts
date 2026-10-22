import { api } from "@/lib/api";
import type { CreateTenantPayload, SchoolAdmin, SchoolAdminSet, SubscriptionPlan, Tenant } from "./types";

export async function listTenants(search?: string): Promise<Tenant[]> {
  const { data } = await api.get<Tenant[]>("/admin/tenants", { params: search ? { search } : undefined });
  return data;
}

export async function getTenant(id: number): Promise<Tenant> {
  const { data } = await api.get<Tenant>(`/admin/tenants/${id}`);
  return data;
}

export async function createTenant(payload: CreateTenantPayload): Promise<Tenant> {
  const { data } = await api.post<Tenant>("/admin/tenants", payload);
  return data;
}

/** PATCH a school. A field set to null clears it; omitted fields are left alone. */
export async function updateTenant(id: number, payload: Record<string, unknown>): Promise<Tenant> {
  const { data } = await api.patch<Tenant>(`/admin/tenants/${id}`, payload);
  return data;
}

export async function listSchoolAdmins(id: number): Promise<SchoolAdmin[]> {
  const { data } = await api.get<SchoolAdmin[]>(`/admin/tenants/${id}/admins`);
  return data;
}

/** Creates the school admin's login, or resets name + password if that
 *  email already exists in the school. */
export async function setSchoolAdmin(id: number, body: SchoolAdminSet): Promise<SchoolAdmin> {
  const { data } = await api.put<SchoolAdmin>(`/admin/tenants/${id}/admin`, body);
  return data;
}

/** Sets a school's logo / profile image (PNG, JPG or SVG). */
export async function uploadTenantLogo(id: number, file: File): Promise<Tenant> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<Tenant>(`/admin/tenants/${id}/logo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** A school's logo as a Blob (the endpoint needs the bearer, so no <img src>). */
export async function fetchTenantLogo(id: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/admin/tenants/${id}/logo`, { responseType: "blob" });
  return data;
}

/** Soft delete: the school is cancelled (logins blocked, data kept). */
export async function deleteTenant(id: number): Promise<Tenant> {
  const { data } = await api.delete<Tenant>(`/admin/tenants/${id}`);
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

export async function extendTrial(id: number, days: number, reason?: string): Promise<Tenant> {
  const { data } = await api.post<Tenant>(`/admin/tenants/${id}/extend-trial`, { days, reason });
  return data;
}

export async function changePlan(id: number, plan_code: string): Promise<Tenant> {
  const { data } = await api.post<Tenant>(`/admin/tenants/${id}/change-plan`, { plan_code });
  return data;
}

export interface TenantUsage {
  tenant_id: number;
  subdomain: string;
  status: string;
  storage_used_mb: number;
  storage_limit_mb: number;
  storage_used_pct: number;
  student_limit: number;
  teacher_limit: number;
  users_count: number;
}

export async function tenantUsage(id: number): Promise<TenantUsage> {
  const { data } = await api.get<TenantUsage>(`/admin/tenants/${id}/usage`);
  return data;
}

export interface AuditEntry {
  id: number;
  tenant_id: number;
  actor_email: string | null;
  actor_role: string | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  summary: string | null;
  ip_address: string | null;
  created_at: string;
}

export async function tenantAudit(id: number, limit = 50): Promise<AuditEntry[]> {
  const { data } = await api.get<AuditEntry[]>(`/admin/tenants/${id}/audit`, { params: { limit } });
  return data;
}

export async function globalAudit(action_prefix?: string, limit = 100): Promise<AuditEntry[]> {
  const { data } = await api.get<AuditEntry[]>("/admin/audit", {
    params: { limit, action_prefix },
  });
  return data;
}

export async function listPlans(): Promise<SubscriptionPlan[]> {
  const { data } = await api.get<SubscriptionPlan[]>("/admin/plans");
  return data;
}

export async function createPlan(payload: PlanWrite): Promise<SubscriptionPlan> {
  const { data } = await api.post<SubscriptionPlan>("/admin/plans", payload);
  return data;
}

export async function updatePlan(id: number, payload: Partial<PlanWrite>): Promise<SubscriptionPlan> {
  const { data } = await api.patch<SubscriptionPlan>(`/admin/plans/${id}`, payload);
  return data;
}

export interface AnalyticsOverview {
  total_tenants: number;
  active_tenants: number;
  trial_tenants: number;
  suspended_tenants: number;
  total_students: number;
  total_teachers: number;
  total_storage_used_mb: number;
  mrr: number;
  by_state: Record<string, number>;
  by_plan: Record<string, number>;
}

export async function analyticsOverview(): Promise<AnalyticsOverview> {
  const { data } = await api.get<AnalyticsOverview>("/admin/analytics/overview");
  return data;
}

export interface PlanWrite {
  code: string;
  name: string;
  monthly_price: number;
  annual_price: number;
  student_limit?: number;
  teacher_limit?: number;
  storage_gb?: number;
  sms_quota?: number;
  modules_included?: string[];
  is_active?: boolean;
}
