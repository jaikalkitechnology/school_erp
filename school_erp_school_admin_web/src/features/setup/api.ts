import { api } from "@/lib/api";

export interface SchoolDashboard {
  school_name: string;
  subdomain: string;
  students_count: number;
  teachers_count: number;
  classes_count: number;
  sections_count: number;
  subjects_count: number;
  departments_count: number;
  storage_used_mb: number;
  storage_limit_mb: number;
  active_year: AcademicYear | null;
}

export interface SchoolSettings {
  school_name: string;
  primary_color: string;
  secondary_color: string;
  logo_url: string | null;
  timezone: string;
  affiliation_board: string | null;
  medium: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  phone: string | null;
  email: string | null;
}

export interface Department {
  id: number;
  name: string;
  code: string | null;
  description: string | null;
  head_user_id: number | null;
}

export interface AcademicTerm {
  id: number;
  year_id: number;
  name: string;
  start_date: string;
  end_date: string;
}

export interface AcademicYear {
  id: number;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  terms: AcademicTerm[];
}

export interface ClassDef {
  id: number;
  code: string;
  name: string;
  stage: "pre_primary" | "primary" | "middle" | "secondary" | "senior_secondary";
  sequence: number;
  department_id: number | null;
}

export interface Section {
  id: number;
  class_def_id: number;
  name: string;
  capacity: number;
  in_charge_user_id: number | null;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  is_core: boolean;
  is_language: boolean;
  has_practical: boolean;
  department_id: number | null;
}

export type HolidayKind = "public" | "school" | "optional" | "vacation";

export interface Holiday {
  id: number;
  date: string;
  name: string;
  kind: HolidayKind;
  description: string | null;
  year_id: number | null;
}

const base = "/v1/school-admin";

export const fetchDashboard = async (): Promise<SchoolDashboard> =>
  (await api.get<SchoolDashboard>(`${base}/dashboard`)).data;

export const fetchSettings = async (): Promise<SchoolSettings> =>
  (await api.get<SchoolSettings>(`${base}/settings`)).data;

export const updateSettings = async (payload: Partial<SchoolSettings>): Promise<SchoolSettings> =>
  (await api.patch<SchoolSettings>(`${base}/settings`, payload)).data;

export const listDepartments = async (): Promise<Department[]> =>
  (await api.get<Department[]>(`${base}/departments`)).data;
export const createDepartment = async (payload: Partial<Department>): Promise<Department> =>
  (await api.post<Department>(`${base}/departments`, payload)).data;
export const deleteDepartment = async (id: number): Promise<void> => {
  await api.delete(`${base}/departments/${id}`);
};

export const listAcademicYears = async (): Promise<AcademicYear[]> =>
  (await api.get<AcademicYear[]>(`${base}/academic-years`)).data;
export const createAcademicYear = async (payload: {
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active?: boolean;
}): Promise<AcademicYear> => (await api.post<AcademicYear>(`${base}/academic-years`, payload)).data;
export const activateAcademicYear = async (id: number): Promise<AcademicYear> =>
  (await api.post<AcademicYear>(`${base}/academic-years/${id}/activate`)).data;
export const addTerm = async (
  year_id: number,
  payload: { name: string; start_date: string; end_date: string },
): Promise<AcademicTerm> =>
  (await api.post<AcademicTerm>(`${base}/academic-years/${year_id}/terms`, payload)).data;

export const listClasses = async (): Promise<ClassDef[]> =>
  (await api.get<ClassDef[]>(`${base}/classes`)).data;
export const createClass = async (payload: Partial<ClassDef>): Promise<ClassDef> =>
  (await api.post<ClassDef>(`${base}/classes`, payload)).data;
export const deleteClass = async (id: number): Promise<void> => {
  await api.delete(`${base}/classes/${id}`);
};

export const listSections = async (class_def_id?: number): Promise<Section[]> =>
  (await api.get<Section[]>(`${base}/sections`, { params: class_def_id ? { class_def_id } : undefined })).data;
export const createSection = async (payload: Partial<Section>): Promise<Section> =>
  (await api.post<Section>(`${base}/sections`, payload)).data;
export const deleteSection = async (id: number): Promise<void> => {
  await api.delete(`${base}/sections/${id}`);
};

export const listSubjects = async (): Promise<Subject[]> =>
  (await api.get<Subject[]>(`${base}/subjects`)).data;
export const createSubject = async (payload: Partial<Subject>): Promise<Subject> =>
  (await api.post<Subject>(`${base}/subjects`, payload)).data;
export const deleteSubject = async (id: number): Promise<void> => {
  await api.delete(`${base}/subjects/${id}`);
};

export const listHolidays = async (year_id?: number): Promise<Holiday[]> =>
  (await api.get<Holiday[]>(`${base}/holidays`, { params: year_id ? { year_id } : undefined })).data;
export const createHoliday = async (payload: Partial<Holiday>): Promise<Holiday> =>
  (await api.post<Holiday>(`${base}/holidays`, payload)).data;
export const deleteHoliday = async (id: number): Promise<void> => {
  await api.delete(`${base}/holidays/${id}`);
};
