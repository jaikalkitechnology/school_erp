import { api } from "@/lib/api";

export type StudentStatus = "active" | "inactive" | "transferred" | "passed_out";
export type Gender = "male" | "female" | "other";
export type Category = "general" | "obc" | "sc" | "st" | "ews";
export type AdmissionStage =
  | "inquiry" | "applied" | "docs_verified" | "offered" | "admitted" | "rejected";

export interface Student {
  id: number;
  admission_number: string;
  roll_no: string | null;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  photo_url: string | null;
  class_def_id: number | null;
  section_id: number | null;
  house_id: number | null;
  admission_date: string | null;
  previous_school: string | null;
  current_class_label: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  aadhaar: string | null;
  religion: string | null;
  caste: string | null;
  category: string | null;
  father_name: string | null;
  mother_name: string | null;
  guardian_name: string | null;
  parent_phone: string | null;
  parent_email: string | null;
  parent_occupation: string | null;
  allergies: string | null;
  medical_conditions: string | null;
  emergency_contact_name: string | null;
  emergency_phone: string | null;
  is_active: boolean;
  status: StudentStatus;
  exit_date: string | null;
  remarks: string | null;
  sibling_group_id: number | null;
}

export interface StudentDocument {
  id: number;
  student_id: number;
  kind: string;
  label: string | null;
  path: string;
  is_verified: boolean;
  notes: string | null;
}

export interface StudentDetail extends Student {
  documents: StudentDocument[];
  sibling_ids: number[];
}

export interface StudentListPage {
  items: Student[];
  total: number;
  limit: number;
  offset: number;
}

export interface StudentCreatePayload {
  full_name: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
  gender?: Gender;
  class_def_id?: number;
  section_id?: number;
  parent_phone?: string;
  parent_email?: string;
  father_name?: string;
  mother_name?: string;
  blood_group?: string;
  address?: string;
  phone?: string;
  admission_number?: string;
  category?: Category;
  photo_url?: string;
}

export interface Admission {
  id: number;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  parent_name: string | null;
  parent_phone: string | null;
  parent_email: string | null;
  desired_class_id: number | null;
  previous_school: string | null;
  notes: string | null;
  stage: AdmissionStage;
  student_id: number | null;
}

const base = "/v1/school-admin/students";
const admBase = "/v1/school-admin/admissions";

export const listStudents = async (params: {
  q?: string;
  class_def_id?: number;
  section_id?: number;
  status?: StudentStatus;
  limit?: number;
  offset?: number;
} = {}): Promise<StudentListPage> => (await api.get<StudentListPage>(base, { params })).data;

export const getStudent = async (id: number): Promise<StudentDetail> =>
  (await api.get<StudentDetail>(`${base}/${id}`)).data;

export const createStudent = async (payload: StudentCreatePayload): Promise<Student> =>
  (await api.post<Student>(base, payload)).data;

export const updateStudent = async (id: number, payload: Partial<StudentCreatePayload> & { status?: StudentStatus }): Promise<Student> =>
  (await api.patch<Student>(`${base}/${id}`, payload)).data;

export const withdrawStudent = async (
  id: number,
  payload: { status: StudentStatus; exit_date?: string; remarks?: string },
): Promise<Student> => (await api.post<Student>(`${base}/${id}/withdraw`, payload)).data;

export const deleteStudent = async (id: number): Promise<void> => {
  await api.delete(`${base}/${id}`);
};

/** Uploads a single file via /v1/uploads and returns the relative path
 * the backend stored it under (tenant_X/students/photos/...). The
 * caller then writes that path to Student.photo_url via updateStudent. */
export const uploadStudentPhoto = async (file: File): Promise<string> => {
  const form = new FormData();
  form.append("file", file);
  form.append("category", "students");
  form.append("subcategory", "photos");
  const res = await api.post<{ path: string }>("/v1/uploads", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data.path;
};

export const transferCertificate = async (id: number) =>
  (await api.get(`${base}/${id}/transfer-certificate`)).data;

export const promoteStudents = async (payload: {
  student_ids: number[];
  target_class_def_id: number;
  target_section_id?: number;
}) => (await api.post(`${base}/promote`, payload)).data;

export const linkSiblings = async (student_ids: number[]) =>
  (await api.post(`${base}/link-siblings`, { student_ids })).data;

export const listDocuments = async (id: number): Promise<StudentDocument[]> =>
  (await api.get<StudentDocument[]>(`${base}/${id}/documents`)).data;

export const addDocument = async (
  id: number,
  payload: { kind: string; label?: string; path: string; notes?: string },
): Promise<StudentDocument> =>
  (await api.post<StudentDocument>(`${base}/${id}/documents`, payload)).data;

export const verifyDocument = async (sid: number, did: number): Promise<StudentDocument> =>
  (await api.post<StudentDocument>(`${base}/${sid}/documents/${did}/verify`)).data;

export const deleteDocument = async (sid: number, did: number): Promise<void> => {
  await api.delete(`${base}/${sid}/documents/${did}`);
};

export const listAdmissions = async (stage?: AdmissionStage): Promise<Admission[]> =>
  (await api.get<Admission[]>(admBase, { params: stage ? { stage } : undefined })).data;

export const createAdmission = async (payload: Partial<Admission>): Promise<Admission> =>
  (await api.post<Admission>(admBase, payload)).data;

export const updateAdmissionStage = async (id: number, stage: AdmissionStage): Promise<Admission> =>
  (await api.patch<Admission>(`${admBase}/${id}`, { stage })).data;

export const admitFromAdmission = async (id: number): Promise<Student> =>
  (await api.post<Student>(`${admBase}/${id}/admit`)).data;
