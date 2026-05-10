import { api } from "@/lib/api";

export type ExamType = "unit_test" | "quarterly" | "half_yearly" | "annual" | "other";
export type ExamStatus = "draft" | "scheduled" | "in_progress" | "completed" | "published";
export type MarkStatus = "pass" | "fail" | "absent" | "exempt";

export interface Exam {
  id: number;
  year_id: number | null;
  term_id: number | null;
  name: string;
  kind: ExamType;
  start_date: string | null;
  end_date: string | null;
  default_max_marks: number;
  status: ExamStatus;
  published_at: string | null;
  notes: string | null;
}

export interface ExamSubject {
  id: number;
  exam_id: number;
  class_def_id: number;
  subject_id: number;
  max_marks: number;
  passing_marks: number;
  exam_date: string | null;
}

export interface RosterRow {
  student_id: number;
  obtained_marks: number | null;
  status: MarkStatus | null;
  remarks: string | null;
}

export interface SectionRoster {
  exam_subject_id: number;
  rows: RosterRow[];
  max_marks: number;
  passing_marks: number;
  student_names: Record<string, string>;
}

export interface ExamResults {
  exam_id: number;
  section_id: number;
  section_average_pct: number;
  students: {
    student_id: number;
    full_name: string;
    admission_number: string;
    subjects: { subject_id: number; max_marks: number; obtained: number | null; status: MarkStatus; grade: string | null }[];
    total_max: number;
    total_obtained: number;
    percentage: number;
    overall_grade: string | null;
    rank_in_section: number | null;
    overall_status: MarkStatus;
  }[];
}

export interface GradeBand {
  min_pct: number;
  grade: string;
  gpa?: number | null;
}

export interface GradeScale {
  id: number;
  code: string;
  name: string;
  bands: GradeBand[];
  is_default: boolean;
}

const base = "/v1/school-admin/exams";

export const listExams = async () => (await api.get<Exam[]>(base)).data;
export const createExam = async (p: Partial<Exam> & { name: string }) =>
  (await api.post<Exam>(base, p)).data;
export const publishExam = async (id: number) =>
  (await api.post<Exam>(`${base}/${id}/publish`)).data;

export const listExamSubjects = async (examId: number) =>
  (await api.get<ExamSubject[]>(`${base}/${examId}/subjects`)).data;
export const scheduleSubject = async (
  examId: number,
  payload: Partial<ExamSubject> & { class_def_id: number; subject_id: number },
) => (await api.post<ExamSubject>(`${base}/${examId}/subjects`, payload)).data;

export const examRoster = async (examSubjectId: number, sectionId: number) =>
  (await api.get<SectionRoster>(`${base}/exam-subjects/${examSubjectId}/roster`, {
    params: { section_id: sectionId },
  })).data;

export const bulkMarks = async (payload: {
  exam_subject_id: number;
  entries: { student_id: number; obtained_marks?: number | null; status?: MarkStatus; remarks?: string }[];
}) => (await api.post(`${base}/marks/bulk`, payload)).data;

export const examResults = async (examId: number, sectionId: number) =>
  (await api.get<ExamResults>(`${base}/${examId}/results`, { params: { section_id: sectionId } })).data;

const gradeBase = "/v1/school-admin/grade-scales";
export const listGradeScales = async () => (await api.get<GradeScale[]>(gradeBase)).data;
export const upsertGradeScale = async (payload: Partial<GradeScale> & { code: string; name: string; bands: GradeBand[] }) =>
  (await api.put<GradeScale>(gradeBase, payload)).data;
