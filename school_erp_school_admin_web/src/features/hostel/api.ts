import { api } from "@/lib/api";

export type HostelKind = "boys" | "girls" | "mixed";
export type RoomStatus = "available" | "full" | "under_maintenance";
export type HostelLeaveStatus = "pending" | "approved" | "rejected" | "returned";
export type DisciplinarySeverity = "note" | "warning" | "suspension";
export type MealType = "breakfast" | "lunch" | "snacks" | "dinner";

export interface Hostel {
  id: number;
  code: string;
  name: string;
  kind: HostelKind;
  warden_user_id: number | null;
  address: string | null;
  is_active: boolean;
}

export interface Room {
  id: number;
  hostel_id: number;
  number: string;
  floor: string | null;
  capacity: number;
  monthly_fee: number;
  status: RoomStatus;
  occupied: number;
}

export interface Allocation {
  id: number;
  student_id: number;
  hostel_id: number;
  room_id: number;
  occupied_from: string;
  occupied_until: string | null;
  monthly_fee: number;
  is_active: boolean;
}

export interface RoomDetail {
  room: Room;
  occupants: { student_id: number; full_name: string; admission_number: string }[];
}

export interface MessMenu {
  id: number;
  hostel_id: number;
  menu_date: string;
  meal: MealType;
  items: string;
}

export interface Visitor {
  id: number;
  hostel_id: number;
  student_id: number;
  visitor_name: string;
  visitor_phone: string | null;
  relation: string | null;
  in_at: string;
  out_at: string | null;
  purpose: string | null;
}

export interface Disciplinary {
  id: number;
  hostel_id: number;
  student_id: number;
  incident_on: string;
  severity: DisciplinarySeverity;
  title: string;
  description: string | null;
  action_taken: string | null;
}

export interface HostelLeave {
  id: number;
  hostel_id: number;
  student_id: number;
  from_date: string;
  to_date: string;
  reason: string;
  status: HostelLeaveStatus;
  decided_at: string | null;
  returned_at: string | null;
  decision_notes: string | null;
}

export interface Reports {
  total_hostels: number;
  total_rooms: number;
  total_capacity: number;
  occupied: number;
  available_seats: number;
  pending_leaves: number;
  open_disciplinary: number;
}

const base = "/v1/school-admin/hostel";

export const listHostels = async () => (await api.get<Hostel[]>(`${base}/hostels`)).data;
export const createHostel = async (p: Partial<Hostel> & { code: string; name: string }) =>
  (await api.post<Hostel>(`${base}/hostels`, p)).data;

export interface HostelWrite {
  code: string;
  name: string;
  kind: HostelKind;
  is_active: boolean;
  warden_user_id?: number | null;
  address?: string | null;
}
export const updateHostel = async (id: number, p: HostelWrite) =>
  (await api.patch<Hostel>(`${base}/hostels/${id}`, p)).data;
/** Refused (409) when the hostel has student stays / leaves / visitors /
 *  discipline records — mark it inactive instead. */
export const deleteHostel = async (id: number) => {
  await api.delete(`${base}/hostels/${id}`);
};

export interface RoomWrite {
  number: string;
  floor: string | null;
  capacity: number;
  monthly_fee: number;
  status: RoomStatus;
}
export const updateRoom = async (id: number, p: RoomWrite) =>
  (await api.patch<Room>(`${base}/rooms/${id}`, p)).data;
/** Refused (409) while students live in it or when it has past stays. */
export const deleteRoom = async (id: number) => {
  await api.delete(`${base}/rooms/${id}`);
};

export const listRooms = async (hostelId: number) =>
  (await api.get<Room[]>(`${base}/hostels/${hostelId}/rooms`)).data;
export const createRoom = async (
  hostelId: number,
  p: Partial<Room> & { number: string; capacity: number },
) => (await api.post<Room>(`${base}/hostels/${hostelId}/rooms`, p)).data;
export const roomDetail = async (roomId: number) =>
  (await api.get<RoomDetail>(`${base}/rooms/${roomId}`)).data;

export const upsertAllocation = async (p: {
  student_id: number;
  room_id: number;
  occupied_from: string;
  monthly_fee?: number;
}) => (await api.post<Allocation>(`${base}/allocations`, p)).data;
export const vacate = async (studentId: number) =>
  (await api.delete(`${base}/allocations/${studentId}`)).data;

export const listMess = async (hostelId: number, on_date?: string) =>
  (await api.get<MessMenu[]>(`${base}/hostels/${hostelId}/mess`, {
    params: on_date ? { on_date } : undefined,
  })).data;
export const upsertMess = async (
  hostelId: number,
  p: { menu_date: string; meal: MealType; items: string },
) => (await api.put<MessMenu>(`${base}/hostels/${hostelId}/mess`, p)).data;

export const listVisitors = async (hostelId: number, open_only = false) =>
  (await api.get<Visitor[]>(`${base}/hostels/${hostelId}/visitors`, {
    params: { open_only },
  })).data;
export const checkInVisitor = async (
  hostelId: number,
  p: { student_id: number; visitor_name: string; visitor_phone?: string; relation?: string; purpose?: string },
) => (await api.post<Visitor>(`${base}/hostels/${hostelId}/visitors`, p)).data;
export const checkOutVisitor = async (visitorId: number) =>
  (await api.post<Visitor>(`${base}/visitors/${visitorId}/checkout`)).data;

export const listDisciplinary = async (hostelId: number, student_id?: number) =>
  (await api.get<Disciplinary[]>(`${base}/hostels/${hostelId}/disciplinary`, {
    params: student_id ? { student_id } : undefined,
  })).data;
export const addDisciplinary = async (
  hostelId: number,
  p: { student_id: number; incident_on: string; severity: DisciplinarySeverity; title: string; description?: string },
) => (await api.post<Disciplinary>(`${base}/hostels/${hostelId}/disciplinary`, p)).data;

export const listLeaves = async (params: {
  hostel_id?: number; status_filter?: HostelLeaveStatus;
} = {}) => (await api.get<HostelLeave[]>(`${base}/leaves`, { params })).data;
export const applyLeave = async (
  hostelId: number,
  p: { student_id: number; from_date: string; to_date: string; reason: string },
) => (await api.post<HostelLeave>(`${base}/hostels/${hostelId}/leaves`, p)).data;
export const decideLeave = async (
  leaveId: number,
  p: { decision: "approved" | "rejected"; decision_notes?: string },
) => (await api.post<HostelLeave>(`${base}/leaves/${leaveId}/decide`, p)).data;
export const markReturned = async (leaveId: number) =>
  (await api.post<HostelLeave>(`${base}/leaves/${leaveId}/return`)).data;

export const reports = async () => (await api.get<Reports>(`${base}/reports`)).data;
