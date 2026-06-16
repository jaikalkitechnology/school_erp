import { api } from "@/lib/api";

export type Audience = "all" | "staff" | "parents" | "students" | "class" | "section";
export type Channel = "in_app" | "sms" | "email" | "push" | "whatsapp";
export type DeliveryStatus = "queued" | "sent" | "failed" | "skipped";

export interface Announcement {
  id: number;
  title: string;
  body: string;
  audience: Audience;
  audience_id: number | null;
  author_user_id: number | null;
  published_at: string | null;
  expires_at: string | null;
  is_pinned: boolean;
}

export interface AnnouncementWrite {
  title: string;
  body: string;
  audience: Audience;
  audience_id?: number;
  is_pinned?: boolean;
  publish?: boolean;
  expires_at?: string;
}

export interface PublishResult {
  announcement_id: number;
  fanned_out_to: number;
}

export interface Template {
  id: number;
  code: string;
  subject_en: string;
  body_en: string;
  subject_hi: string | null;
  body_hi: string | null;
  subject_mr: string | null;
  body_mr: string | null;
  channels: Channel[];
  is_active: boolean;
}

export interface OutboxRow {
  id: number;
  notification_id: number | null;
  recipient_user_id: number;
  channel: Channel;
  address: string | null;
  subject: string | null;
  body: string;
  status: DeliveryStatus;
  provider_ref: string | null;
  error: string | null;
  created_at: string;
}

const base = "/v1/school-admin/communication";

export const listTemplates = async () => (await api.get<Template[]>(`${base}/templates`)).data;
export const upsertTemplate = async (code: string, payload: Omit<Template, "id" | "is_active">) =>
  (await api.put<Template>(`${base}/templates/${code}`, payload)).data;

export const listAnnouncements = async () =>
  (await api.get<Announcement[]>(`${base}/announcements`)).data;
export const createAnnouncement = async (payload: AnnouncementWrite) =>
  (await api.post<PublishResult>(`${base}/announcements`, payload)).data;
export const deleteAnnouncement = async (id: number) =>
  (await api.delete<{ deleted: number; notifications_removed: number }>(
    `${base}/announcements/${id}`,
  )).data;
export const bulkDeleteAnnouncements = async (ids: number[]) =>
  (await api.post<{
    deleted: number[];
    skipped: number[];
    notifications_removed: number;
  }>(`${base}/announcements/bulk-delete`, { ids })).data;

export const listOutbox = async (status?: DeliveryStatus) =>
  (await api.get<OutboxRow[]>(`${base}/outbox`, { params: status ? { status } : undefined })).data;
