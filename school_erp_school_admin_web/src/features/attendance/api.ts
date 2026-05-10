import { api } from "@/lib/api";

export type AttendanceStatus = "present" | "absent" | "late" | "leave" | "half_day";

export interface RollEntry {
  student_id: number;
  full_name: string;
  admission_number: string;
  roll_no: string | null;
  status: AttendanceStatus;
  remarks: string | null;
}

export interface SectionRoll {
  section_id: number;
  date: string;
  period: string;
  students: RollEntry[];
  counts: Record<string, number>;
}

export interface MonthlyStudent {
  student_id: number;
  full_name: string;
  admission_number: string;
  total_days: number;
  present: number;
  absent: number;
  late: number;
  leave: number;
  half_day: number;
  attendance_pct: number;
}

export interface MonthlyReport {
  section_id: number;
  year: number;
  month: number;
  working_days: number;
  students: MonthlyStudent[];
}

export interface Defaulter {
  student_id: number;
  full_name: string;
  admission_number: string;
  section_id: number | null;
  class_def_id: number | null;
  total_days: number;
  present_days: number;
  attendance_pct: number;
}

const base = "/v1/school-admin/attendance";

export const sectionRoll = async (sectionId: number, date: string, period = "day"): Promise<SectionRoll> =>
  (await api.get<SectionRoll>(`${base}/section/${sectionId}`, { params: { date, period } })).data;

export const markRoll = async (payload: {
  section_id: number;
  date: string;
  period?: string;
  default_status?: AttendanceStatus;
  entries: { student_id: number; status: AttendanceStatus; remarks?: string }[];
}): Promise<SectionRoll> => (await api.post<SectionRoll>(`${base}/mark`, payload)).data;

export const sectionMonthly = async (sectionId: number, year: number, month: number): Promise<MonthlyReport> =>
  (await api.get<MonthlyReport>(`${base}/section/${sectionId}/monthly`, { params: { year, month } })).data;

export const defaulterList = async (params: {
  threshold_pct?: number;
  section_id?: number;
  start?: string;
  end?: string;
}): Promise<Defaulter[]> => (await api.get<Defaulter[]>(`${base}/defaulters`, { params })).data;
