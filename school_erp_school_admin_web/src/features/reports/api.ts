import { api } from "@/lib/api";

export interface TrendPoint {
  label: string;
  value: number;
}

export interface AnalyticsOverview {
  students: number;
  teachers: number;
  classes: number;
  sections: number;
  attendance_today_pct: number;
  fee_collected_this_month: number;
  fee_pending: number;
  overdue_loans: number;
  by_class_strength: TrendPoint[];
}

export interface AttendanceTrend {
  points: TrendPoint[];
  average_pct: number;
}

export interface FeeOverview {
  total_billed: number;
  total_collected: number;
  pending: number;
  overdue_count: number;
  by_method: TrendPoint[];
  by_category: TrendPoint[];
}

export interface ExamSummaryRow {
  exam_id: number;
  exam_name: string;
  section_id: number | null;
  section_name: string | null;
  average_pct: number;
  pass_pct: number;
  student_count: number;
}

export interface ExamAnalytics {
  rows: ExamSummaryRow[];
  grade_distribution: TrendPoint[];
}

export interface LibraryUsage {
  issued_today: number;
  overdue: number;
  most_loaned: TrendPoint[];
}

export interface TransportSummary {
  routes: number;
  buses: number;
  drivers: number;
  students_allocated: number;
  active_trips_today: number;
}

export interface HostelSummary {
  occupied: number;
  available_seats: number;
  pending_leaves: number;
}

export interface StudentReportRow {
  student_id: number;
  admission_number: string;
  full_name: string;
  class_label: string | null;
  section_name: string | null;
  parent_phone: string | null;
  status: string;
}

const base = "/v1/school-admin/analytics";

export const overview = async () => (await api.get<AnalyticsOverview>(`${base}/overview`)).data;
export const attendanceTrend = async (days = 14) =>
  (await api.get<AttendanceTrend>(`${base}/attendance-trend`, { params: { days } })).data;
export const fees = async () => (await api.get<FeeOverview>(`${base}/fees`)).data;
export const examAnalytics = async (exam_id?: number) =>
  (await api.get<ExamAnalytics>(`${base}/exams`, {
    params: exam_id ? { exam_id } : undefined,
  })).data;
export const libraryUsage = async () => (await api.get<LibraryUsage>(`${base}/library`)).data;
export const transportSummary = async () =>
  (await api.get<TransportSummary>(`${base}/transport`)).data;
export const hostelSummary = async () =>
  (await api.get<HostelSummary>(`${base}/hostel`)).data;

export const studentReport = async (params: {
  class_def_id?: number;
  section_id?: number;
  only_active?: boolean;
} = {}) =>
  (await api.get<{ rows: StudentReportRow[] }>(`${base}/reports/students`, { params })).data.rows;

export const studentReportCsvUrl = (params: {
  class_def_id?: number;
  section_id?: number;
  only_active?: boolean;
}) => {
  const qs = new URLSearchParams();
  if (params.class_def_id !== undefined) qs.set("class_def_id", String(params.class_def_id));
  if (params.section_id !== undefined) qs.set("section_id", String(params.section_id));
  if (params.only_active !== undefined) qs.set("only_active", String(params.only_active));
  return `${base}/reports/students.csv${qs.toString() ? `?${qs}` : ""}`;
};
