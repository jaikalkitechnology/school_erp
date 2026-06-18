import { api } from "@/lib/api";

export interface UserRow {
  id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  last_login_at: string | null;
  avatar_url: string | null;
  role_codes: string[];
  granted_admin_pages: string[];
}

export interface AdminPageOption {
  slug: string;
  label: string;
  group: string;
}

export interface PagesCatalogue {
  pages: AdminPageOption[];
  defaults_by_role: Record<string, string[]>;
}

export interface UserListPage {
  items: UserRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RoleOption {
  code: string;
  name: string;
}

const base = "/v1/school-admin/users";

export const listAssignableRoles = async (): Promise<RoleOption[]> =>
  (await api.get<RoleOption[]>(`${base}/_roles`)).data;

export const listAdminPages = async (): Promise<PagesCatalogue> =>
  (await api.get<PagesCatalogue>(`${base}/_pages`)).data;

export const listAdminUsers = async (params: {
  q?: string;
  role_code?: string;
  only_active?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<UserListPage> =>
  (await api.get<UserListPage>(base, { params })).data;

export const createAdminUser = async (payload: {
  full_name: string;
  email?: string;
  phone?: string;
  password: string;
  role_codes: string[];
  granted_admin_pages?: string[];
}): Promise<UserRow> => (await api.post<UserRow>(base, payload)).data;

export const updateAdminUser = async (
  id: number,
  payload: {
    full_name?: string;
    email?: string;
    phone?: string;
    role_codes?: string[];
    granted_admin_pages?: string[];
  },
): Promise<UserRow> => (await api.patch<UserRow>(`${base}/${id}`, payload)).data;

export const setUserPassword = async (id: number, new_password: string): Promise<void> => {
  await api.post(`${base}/${id}/set-password`, { new_password });
};

export const activateUser = async (id: number): Promise<UserRow> =>
  (await api.post<UserRow>(`${base}/${id}/activate`)).data;

export const deactivateUser = async (id: number): Promise<UserRow> =>
  (await api.post<UserRow>(`${base}/${id}/deactivate`)).data;

export const deleteAdminUser = async (id: number): Promise<void> => {
  await api.delete(`${base}/${id}`);
};
