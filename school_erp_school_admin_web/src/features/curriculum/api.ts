import { api } from "@/lib/api";

export interface House {
  id: number;
  name: string;
  code: string | null;
  color: string;
  motto: string | null;
  captain_user_id: number | null;
}

export interface SectionSubject {
  id: number;
  section_id: number;
  subject_id: number;
  teacher_user_id: number | null;
  weekly_periods: number;
  is_optional: boolean;
}

export type CalendarKind = "general" | "exam" | "sports" | "cultural" | "parent_teacher" | "holiday";

export interface CalendarEvent {
  id: number;
  title: string;
  description: string | null;
  kind: CalendarKind;
  starts_at: string;
  ends_at: string | null;
  is_all_day: boolean;
  year_id: number | null;
  term_id: number | null;
  audience: string;
}

export interface Chapter {
  id: number;
  syllabus_id: number;
  sequence: number;
  title: string;
  summary: string | null;
  expected_periods: number;
  target_completion_date: string | null;
  completion_pct: number;
  completed_on: string | null;
}

export interface Syllabus {
  id: number;
  year_id: number;
  class_def_id: number;
  subject_id: number;
  title: string;
  description: string | null;
  chapters: Chapter[];
  overall_completion_pct: number;
}

const base = "/v1/school-admin/curriculum";

export const listHouses = async (): Promise<House[]> => (await api.get<House[]>(`${base}/houses`)).data;
export const createHouse = async (payload: Partial<House>): Promise<House> =>
  (await api.post<House>(`${base}/houses`, payload)).data;
export const deleteHouse = async (id: number): Promise<void> => {
  await api.delete(`${base}/houses/${id}`);
};

export const listSectionSubjects = async (section_id?: number): Promise<SectionSubject[]> =>
  (await api.get<SectionSubject[]>(`${base}/section-subjects`, { params: section_id ? { section_id } : undefined })).data;
export const bulkLinkSectionSubjects = async (
  section_id: number,
  subject_ids: number[],
  weekly_periods = 4,
): Promise<SectionSubject[]> =>
  (await api.post<SectionSubject[]>(`${base}/section-subjects/bulk`, { section_id, subject_ids, weekly_periods })).data;
export const deleteSectionSubject = async (id: number): Promise<void> => {
  await api.delete(`${base}/section-subjects/${id}`);
};

export const listEvents = async (year_id?: number): Promise<CalendarEvent[]> =>
  (await api.get<CalendarEvent[]>(`${base}/events`, { params: year_id ? { year_id } : undefined })).data;
export const createEvent = async (payload: Partial<CalendarEvent>): Promise<CalendarEvent> =>
  (await api.post<CalendarEvent>(`${base}/events`, payload)).data;
export const deleteEvent = async (id: number): Promise<void> => {
  await api.delete(`${base}/events/${id}`);
};

export const listSyllabi = async (params?: {
  year_id?: number;
  class_def_id?: number;
  subject_id?: number;
}): Promise<Syllabus[]> => (await api.get<Syllabus[]>(`${base}/syllabi`, { params })).data;

export const createSyllabus = async (payload: {
  year_id: number;
  class_def_id: number;
  subject_id: number;
  title: string;
  description?: string;
}): Promise<Syllabus> => (await api.post<Syllabus>(`${base}/syllabi`, payload)).data;

export const deleteSyllabus = async (id: number): Promise<void> => {
  await api.delete(`${base}/syllabi/${id}`);
};

export const addChapter = async (
  syllabus_id: number,
  payload: { sequence: number; title: string; expected_periods: number; summary?: string; target_completion_date?: string },
): Promise<Chapter> => (await api.post<Chapter>(`${base}/syllabi/${syllabus_id}/chapters`, payload)).data;

export const setChapterProgress = async (
  chapter_id: number,
  completion_pct: number,
): Promise<Chapter> =>
  (await api.patch<Chapter>(`${base}/chapters/${chapter_id}/progress`, { completion_pct })).data;
