import { api } from "@/lib/api";

/** In-app notifications for the signed-in user (/v1/notifications). */
export interface AppNotification {
  id: number;
  title: string;
  body: string;
  kind: string;
  deeplink: string | null;
  source_type: string | null;
  source_id: number | null;
  read_at: string | null;
  created_at: string;
}

export const listNotifications = async (
  params: { only_unread?: boolean; limit?: number } = {},
) => (await api.get<AppNotification[]>("/v1/notifications", { params })).data;

export const markNotificationRead = async (id: number) =>
  (await api.post<AppNotification>(`/v1/notifications/${id}/read`)).data;

export const markAllNotificationsRead = async () =>
  (await api.post<{ marked: number }>("/v1/notifications/read-all")).data;
