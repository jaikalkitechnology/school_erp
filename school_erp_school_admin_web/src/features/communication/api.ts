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
  // Particular people (staff / parents / students audiences); null = everyone in it.
  recipient_user_ids?: number[] | null;
}

export interface AnnouncementWrite {
  title: string;
  body: string;
  audience: Audience;
  audience_id?: number;
  is_pinned?: boolean;
  publish?: boolean;
  expires_at?: string;
  // Per-announcement push toggle. Omit / null → use the template
  // default. true / false → force or silence push for this one.
  send_push?: boolean | null;
  recipient_user_ids?: number[] | null;
}

export interface PublishResult {
  announcement_id: number;
  fanned_out_to: number;
  // Phones actually reached via FCM (drain ran synchronously inside
  // the publish handler). Zero if every recipient has no active
  // device, or if FCM is misconfigured.
  push_sent: number;
  // Sends FCM rejected (dead token, mismatched-credential, etc).
  push_failed: number;
  // Recipients who got no push (no phone signed in, or FCM off).
  push_skipped: number;
  // Set when the server can't send pushes at all (eg. Firebase key missing).
  push_unavailable_reason: string | null;
}

export interface PushStatus {
  available: boolean;
  reason: string | null;
  active_devices: number;
  users_with_devices: number;
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

export const getPushStatus = async () => (await api.get<PushStatus>(`${base}/push-status`)).data;
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

// ---- 1-on-1 messages (inbox + sent for the logged-in admin) -------------
// Reads off the platform-level /v1/messages router so the admin sees the
// same teacher → admin messages the teacher app sends. No tenant prefix:
// these messages are user-scoped, not surface-scoped.

export interface DirectMessage {
  id: number;
  sender_user_id: number | null;
  recipient_user_id: number;
  subject: string | null;
  body: string;
  read_at: string | null;
  created_at: string;
  sender_name?: string;
  sender_full_name?: string;
}

export const listInboxMessages = async () =>
  (await api.get<DirectMessage[]>(`/v1/messages`)).data;

export const listSentMessages = async () =>
  (await api.get<DirectMessage[]>(`/v1/messages/sent`)).data;

export const sendDirectMessage = async (payload: {
  recipient_user_id: number;
  body: string;
  subject?: string;
}) => (await api.post<DirectMessage>(`/v1/messages`, payload)).data;

export const markMessageRead = async (id: number) =>
  (await api.post<DirectMessage>(`/v1/messages/${id}/read`)).data;
