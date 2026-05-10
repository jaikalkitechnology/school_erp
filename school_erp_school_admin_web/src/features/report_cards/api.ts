import { api } from "@/lib/api";

export type Board = "cbse" | "icse" | "state" | "custom";
export type ReportCardStatus = "draft" | "generated" | "published";

export interface Template {
  id: number;
  code: string;
  name: string;
  board: Board;
  layout: Record<string, unknown>;
  is_default: boolean;
}

export interface CoCurricularGrade {
  id: number;
  exam_id: number;
  student_id: number;
  area: string;
  grade: string;
  remarks: string | null;
}

export interface Remark {
  id: number;
  exam_id: number;
  student_id: number;
  teacher_remark: string | null;
  principal_remark: string | null;
}

export interface ReportCard {
  id: number;
  exam_id: number;
  student_id: number;
  template_id: number | null;
  status: ReportCardStatus;
  total_marks: number | null;
  obtained_marks: number | null;
  percentage: number | null;
  overall_grade: string | null;
  rank_in_section: number | null;
  snapshot: {
    exam_name?: string;
    student?: { full_name?: string; admission_number?: string };
    co_curricular?: { area: string; grade: string; remarks?: string | null }[];
    remarks?: { teacher_remark?: string | null; principal_remark?: string | null };
  };
  pdf_path: string | null;
  generated_at: string | null;
  published_at: string | null;
}

export interface GenerateResult {
  generated: number;
  skipped: number;
  skipped_reasons: string[];
}

const base = "/v1/school-admin/report-cards";

export const listTemplates = async () =>
  (await api.get<Template[]>(`${base}/templates`)).data;
export const upsertTemplate = async (p: Partial<Template> & { code: string; name: string }) =>
  (await api.put<Template>(`${base}/templates`, p)).data;
export const deleteTemplate = async (id: number) =>
  (await api.delete(`${base}/templates/${id}`)).data;

export const listCoCurricular = async (examId: number, sectionId: number) =>
  (await api.get<CoCurricularGrade[]>(`${base}/${examId}/co-curricular`, {
    params: { section_id: sectionId },
  })).data;
export const upsertCoCurricular = async (
  examId: number,
  payload: { student_id: number; area: string; grade: string; remarks?: string },
) => (await api.post<CoCurricularGrade>(`${base}/${examId}/co-curricular`, payload)).data;

export const listRemarks = async (examId: number, sectionId: number) =>
  (await api.get<Remark[]>(`${base}/${examId}/remarks`, {
    params: { section_id: sectionId },
  })).data;
export const upsertRemark = async (
  examId: number,
  payload: { student_id: number; teacher_remark?: string; principal_remark?: string },
) => (await api.post<Remark>(`${base}/${examId}/remarks`, payload)).data;

export const generate = async (payload: {
  exam_id: number;
  section_id: number;
  template_id?: number;
  publish?: boolean;
}) => (await api.post<GenerateResult>(`${base}/generate`, payload)).data;

export const publishSection = async (examId: number, sectionId: number) =>
  (await api.post<{ published: number }>(
    `${base}/${examId}/sections/${sectionId}/publish`,
  )).data;

export const listSectionCards = async (examId: number, sectionId: number) =>
  (await api.get<ReportCard[]>(`${base}/${examId}/sections/${sectionId}`)).data;

export const pdfUrl = (cardId: number) => `${base}/${cardId}/pdf`;
