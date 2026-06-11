import { api } from "@/lib/api";

export type SubmissionStatus = "submitted" | "graded" | "late" | "missing";

export interface Homework {
  id: number;
  section_id: number;
  subject_id: number | null;
  teacher_user_id: number | null;
  title: string;
  description: string | null;
  assigned_on: string;
  due_date: string;
  max_marks: number;
  attachments: string[];
}

export interface Submission {
  id: number;
  homework_id: number;
  student_id: number;
  submitted_at: string | null;
  content: string | null;
  attachments: string[];
  status: SubmissionStatus;
  marks: number | null;
  feedback: string | null;
  graded_at: string | null;
}

export interface StudentSubmissionStatus {
  student_id: number;
  full_name: string;
  admission_number: string;
  submitted: boolean;
  submitted_at: string | null;
  status: SubmissionStatus | null;
  marks: number | null;
}

export interface HomeworkReport {
  homework_id: number;
  section_id: number;
  title: string;
  due_date: string;
  max_marks: number | string | null;
  rows: StudentSubmissionStatus[];
  submitted_count: number;
  total_students: number;
}

const base = "/v1/school-admin/homework";

export const listHomework = async (params: { section_id?: number; teacher_user_id?: number; upcoming_only?: boolean }) =>
  (await api.get<Homework[]>(base, { params })).data;

export const createHomework = async (payload: Partial<Homework> & { section_id: number; title: string; due_date: string }) =>
  (await api.post<Homework>(base, payload)).data;

export const updateHomework = async (id: number, payload: Partial<Homework>) =>
  (await api.patch<Homework>(`${base}/${id}`, payload)).data;

export const deleteHomework = async (id: number) => {
  await api.delete(`${base}/${id}`);
};

export const submissionsFor = async (homeworkId: number) =>
  (await api.get<Submission[]>(`${base}/${homeworkId}/submissions`)).data;

export const homeworkReport = async (homeworkId: number) =>
  (await api.get<HomeworkReport>(`${base}/${homeworkId}/report`)).data;

export const grade = async (submissionId: number, payload: { marks: number; feedback?: string }) =>
  (await api.post<Submission>(`${base}/submissions/${submissionId}/grade`, payload)).data;
