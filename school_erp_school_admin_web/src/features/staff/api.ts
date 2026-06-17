import { api } from "@/lib/api";

export type StaffAttendanceStatus = "present" | "absent" | "leave" | "half_day";

export interface StaffRollRow {
  teacher_id: number;
  employee_no: string;
  full_name: string;
  photo_url: string | null;
  designation: string | null;
  status: StaffAttendanceStatus | null;
  remarks: string | null;
}

export interface StaffRoll {
  date: string;
  rows: StaffRollRow[];
}

export type StaffLeaveStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "cancelled";

export interface StaffLeave {
  id: number;
  user_id: number;
  full_name: string;
  employee_no: string | null;
  designation: string | null;
  start_date: string;
  end_date: string;
  reason: string;
  kind: string;
  status: StaffLeaveStatus;
  decision_remarks: string | null;
  decided_at: string | null;
}

const base = "/v1/school-admin/teachers";

export const getStaffRoll = async (date?: string): Promise<StaffRoll> =>
  (await api.get<StaffRoll>(`${base}/attendance/roll`, {
    params: date ? { date } : undefined,
  })).data;

export const submitStaffRoll = async (payload: {
  date: string;
  entries: { teacher_id: number; status: StaffAttendanceStatus; remarks?: string }[];
}): Promise<{ written: number }> =>
  (await api.post<{ written: number }>(`${base}/attendance/bulk`, payload)).data;

export const listStaffLeaves = async (status?: StaffLeaveStatus): Promise<StaffLeave[]> =>
  (await api.get<StaffLeave[]>(`${base}/staff-leaves`, {
    params: status ? { status } : undefined,
  })).data;

export const decideStaffLeave = async (
  id: number,
  payload: { status: "approved" | "rejected"; decision_remarks?: string },
): Promise<StaffLeave> =>
  (await api.post<StaffLeave>(`${base}/staff-leaves/${id}/decide`, payload)).data;
