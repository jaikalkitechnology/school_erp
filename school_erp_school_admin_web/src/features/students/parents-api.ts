import { api } from "@/lib/api";

export type Relation = "father" | "mother" | "guardian" | "other";
export type AccessLevel = "primary" | "secondary" | "guardian";

export interface ParentLinkRead {
  mapping_id: number;
  parent_id: number;
  parent_user_id: number;
  parent_name: string;
  parent_phone: string | null;
  parent_email: string | null;
  relation: Relation;
  access_level: AccessLevel;
  is_primary: boolean;
  can_pay_fee: boolean;
  can_receive_notifications: boolean;
}

export interface ParentLinkPayload {
  parent_user_id: number;
  relation: Relation;
  access_level: AccessLevel;
  is_primary: boolean;
  can_pay_fee: boolean;
  can_receive_notifications: boolean;
}

export interface ParentCreatePayload {
  full_name: string;
  email?: string;
  phone?: string;
  password: string;
  relation?: Relation;
  occupation?: string;
}

export interface ParentSelf {
  parent_id: number;
  user_id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
  relation: Relation;
  current_child_id: number | null;
}

export const listStudentParents = async (studentId: number): Promise<ParentLinkRead[]> =>
  (await api.get<ParentLinkRead[]>(`/v1/school-admin/students/${studentId}/parents`)).data;

export const linkStudentParent = async (
  studentId: number,
  payload: ParentLinkPayload,
): Promise<ParentLinkRead> =>
  (await api.post<ParentLinkRead>(`/v1/school-admin/students/${studentId}/parents`, payload)).data;

export const unlinkStudentParent = async (studentId: number, mappingId: number): Promise<void> => {
  await api.delete(`/v1/school-admin/students/${studentId}/parents/${mappingId}`);
};

export const createParent = async (payload: ParentCreatePayload): Promise<ParentSelf> =>
  (await api.post<ParentSelf>("/v1/school-admin/parents", payload)).data;
