import { api } from "@/lib/api";

export interface Cell {
  id?: number;
  day_of_week: number;
  period_number: number;
  subject_id: number | null;
  teacher_user_id: number | null;
  room: string | null;
  notes?: string | null;
}

export interface SectionTimetable {
  section_id: number;
  cells: Cell[];
}

export interface CellConflict {
  day_of_week: number;
  period_number: number;
  teacher_user_id: number;
  other_section_id: number;
}

export interface SaveResult {
  saved: number;
  conflicts: CellConflict[];
}

export interface PeriodDef {
  id: number;
  day_of_week: number;
  period_number: number;
  label: string | null;
  starts_at: string | null;
  ends_at: string | null;
  is_break: boolean;
}

export type SubStatus = "pending" | "assigned" | "completed" | "cancelled";

export interface Substitution {
  id: number;
  date: string;
  section_id: number;
  period_number: number;
  subject_id: number | null;
  original_teacher_user_id: number | null;
  substitute_teacher_user_id: number | null;
  status: SubStatus;
  reason: string | null;
}

export interface SubSuggestion {
  date: string;
  absent_teacher_user_id: number;
  entries: {
    section_id: number;
    period_number: number;
    subject_id: number | null;
    suggested_substitutes: number[];
  }[];
}

const base = "/v1/school-admin/timetable";

export const listPeriods = async () => (await api.get<PeriodDef[]>(`${base}/periods`)).data;
export const upsertPeriod = async (p: Partial<PeriodDef>) => (await api.put<PeriodDef>(`${base}/periods`, p)).data;
export const deletePeriod = async (id: number) => { await api.delete(`${base}/periods/${id}`); };

export const sectionTimetable = async (sectionId: number) =>
  (await api.get<SectionTimetable>(`${base}/sections/${sectionId}`)).data;
export const saveSection = async (sectionId: number, cells: Cell[]) =>
  (await api.put<SaveResult>(`${base}/sections/${sectionId}`, { cells })).data;

export const teacherTimetable = async (teacherUserId: number) =>
  (await api.get(`${base}/teachers/${teacherUserId}`)).data;

export const suggestSubs = async (date: string, teacher_user_id: number) =>
  (await api.post<SubSuggestion>(`${base}/substitutions/suggest`, { date, teacher_user_id })).data;

export const listSubsForDate = async (target_date: string) =>
  (await api.get<Substitution[]>(`${base}/substitutions`, { params: { target_date } })).data;

export const assignSub = async (payload: {
  date: string; section_id: number; period_number: number;
  substitute_teacher_user_id: number; reason?: string;
}) => (await api.post<Substitution>(`${base}/substitutions`, payload)).data;

export const completeSub = async (id: number) =>
  (await api.post<Substitution>(`${base}/substitutions/${id}/complete`)).data;

export const cancelSub = async (id: number) =>
  (await api.post<Substitution>(`${base}/substitutions/${id}/cancel`)).data;
