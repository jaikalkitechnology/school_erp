import { api } from "@/lib/api";

export type EmploymentStatus = "active" | "on_leave" | "resigned";
export type AttendanceStatus = "present" | "absent" | "leave" | "half_day";

export interface Teacher {
  id: number;
  user_id: number;
  employee_no: string;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  photo_url: string | null;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  emergency_contact: string | null;
  emergency_phone: string | null;
  department_id: number | null;
  designation: string | null;
  date_of_joining: string | null;
  qualifications: string[];
  experience_years: number;
  employment_status: EmploymentStatus;
  is_class_teacher: boolean;
  is_available_for_substitution: boolean;
  notes: string | null;
}

export interface TeacherListPage {
  items: Teacher[];
  total: number;
  limit: number;
  offset: number;
}

export interface TeacherCreatePayload {
  full_name: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  password: string;
  qualifications?: string[];
  experience_years?: number;
  department_id?: number;
  designation?: string;
  date_of_joining?: string;
  is_class_teacher?: boolean;
  is_available_for_substitution?: boolean;
  role_codes?: string[];
  employee_no?: string;
  photo_url?: string;
}

export interface WorkloadEntry {
  section_subject_id: number;
  section_id: number;
  section_name: string;
  class_def_id: number;
  class_name: string;
  subject_id: number;
  subject_name: string;
  weekly_periods: number;
}

export interface Workload {
  teacher_id: number;
  user_id: number;
  full_name: string;
  weekly_periods_total: number;
  classes_handled: number;
  subjects_taught: number;
  is_class_teacher_of_section: number | null;
  entries: WorkloadEntry[];
}

export interface SubCandidate {
  teacher_id: number;
  user_id: number;
  full_name: string;
  qualifications: string[];
  weekly_periods_total: number;
  is_available_for_substitution: boolean;
  is_present: boolean;
}

export interface AttendanceRow {
  id: number;
  teacher_id: number;
  date: string;
  status: AttendanceStatus;
  remarks: string | null;
}

const base = "/v1/school-admin/teachers";

export const listTeachers = async (params: {
  q?: string;
  department_id?: number;
  status?: EmploymentStatus;
  limit?: number;
  offset?: number;
} = {}): Promise<TeacherListPage> => (await api.get<TeacherListPage>(base, { params })).data;

export const getTeacher = async (id: number): Promise<Teacher> =>
  (await api.get<Teacher>(`${base}/${id}`)).data;

export const createTeacher = async (payload: TeacherCreatePayload): Promise<Teacher> =>
  (await api.post<Teacher>(base, payload)).data;

export const updateTeacher = async (
  id: number,
  payload: Partial<TeacherCreatePayload> & { employment_status?: EmploymentStatus },
): Promise<Teacher> => (await api.patch<Teacher>(`${base}/${id}`, payload)).data;

export const deleteTeacher = async (id: number): Promise<void> => {
  await api.delete(`${base}/${id}`);
};

export const setQualifiedSubjects = async (
  id: number,
  subject_ids: number[],
): Promise<{ id: number; teacher_id: number; subject_id: number; is_primary: boolean }[]> =>
  (await api.put(`${base}/${id}/qualified-subjects`, { subject_ids })).data;

export const listQualifiedSubjects = async (
  id: number,
): Promise<{ id: number; teacher_id: number; subject_id: number; is_primary: boolean }[]> =>
  (await api.get(`${base}/${id}/qualified-subjects`)).data;

export const assignSectionSubject = async (id: number, section_subject_id: number) =>
  (await api.post(`${base}/${id}/assign-section-subject`, { section_subject_id })).data;

export const clearSectionSubjectTeacher = async (section_subject_id: number) =>
  (await api.delete(`${base}/section-subjects/${section_subject_id}/teacher`)).data;

export const assignClassTeacher = async (id: number, section_id: number) =>
  (await api.post(`${base}/${id}/assign-class-teacher`, { section_id })).data;

export const getWorkload = async (id: number): Promise<Workload> =>
  (await api.get<Workload>(`${base}/${id}/workload`)).data;

export const upsertAttendance = async (
  id: number,
  payload: { date: string; status: AttendanceStatus; remarks?: string },
): Promise<AttendanceRow> => (await api.post<AttendanceRow>(`${base}/${id}/attendance`, payload)).data;

export const listAttendance = async (id: number, params: { start?: string; end?: string } = {}): Promise<AttendanceRow[]> =>
  (await api.get<AttendanceRow[]>(`${base}/${id}/attendance`, { params })).data;

export const substitutionPool = async (target_date: string, subject_id?: number): Promise<SubCandidate[]> =>
  (await api.get<SubCandidate[]>(`${base}/substitution-pool`, { params: { target_date, subject_id } })).data;

/** Uploads a teacher photo to /v1/uploads and returns the relative
 * path the backend stored it under (tenant_X/teachers/photos/...).
 * Save the returned string to Teacher.photo_url via updateTeacher /
 * createTeacher. */
export const uploadTeacherPhoto = async (file: File): Promise<string> => {
  const form = new FormData();
  form.append("file", file);
  form.append("category", "teachers");
  form.append("subcategory", "photos");
  const res = await api.post<{ path: string }>("/v1/uploads", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data.path;
};
