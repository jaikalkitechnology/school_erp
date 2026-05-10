import { api } from "@/lib/api";

export type FeePeriod = "one_time" | "monthly" | "quarterly" | "annual";
export type InvoiceStatus = "pending" | "partial" | "paid" | "overdue" | "waived" | "cancelled";
export type PaymentMethod = "cash" | "upi" | "card" | "netbanking" | "cheque" | "bank_transfer";

export interface FeeCategory {
  id: number;
  code: string;
  name: string;
  is_recurring: boolean;
  description: string | null;
}

export interface FeeStructure {
  id: number;
  class_def_id: number;
  category_id: number;
  period: FeePeriod;
  amount: number;
  due_day_of_month: number;
  late_fee_per_day: number;
  grace_days: number;
  notes: string | null;
}

export interface FeeInvoice {
  id: number;
  student_id: number;
  category_id: number | null;
  invoice_number: string;
  period_start: string;
  period_end: string;
  due_date: string;
  base_amount: number;
  discount_amount: number;
  late_fee_amount: number;
  total_amount: number;
  paid_amount: number;
  status: InvoiceStatus;
}

export interface StudentFeeView {
  student_id: number;
  full_name: string;
  invoices: FeeInvoice[];
  total_due: number;
  total_paid: number;
  overdue_count: number;
}

export interface DailyCollectionRow {
  date: string;
  payments: number;
  amount: number;
}

export interface CollectionSummary {
  start: string;
  end: string;
  total_collected: number;
  total_pending: number;
  overdue_amount: number;
  daily: DailyCollectionRow[];
  by_method: Record<string, number>;
  by_category: Record<string, number>;
}

export interface DefaulterRow {
  student_id: number;
  full_name: string;
  admission_number: string;
  invoices_overdue: number;
  amount_overdue: number;
}

const base = "/v1/school-admin/fees";

export const listCategories = async () => (await api.get<FeeCategory[]>(`${base}/categories`)).data;
export const createCategory = async (p: Partial<FeeCategory>) =>
  (await api.post<FeeCategory>(`${base}/categories`, p)).data;

export const listStructures = async (class_def_id?: number) =>
  (await api.get<FeeStructure[]>(`${base}/structures`, { params: class_def_id ? { class_def_id } : undefined })).data;
export const createStructure = async (p: Partial<FeeStructure>) =>
  (await api.post<FeeStructure>(`${base}/structures`, p)).data;
export const generateInvoices = async (
  structureId: number,
  payload: {
    period_start: string;
    period_end: string;
    sibling_discount_pct?: number;
    apply_sibling_discount?: boolean;
  },
) => (await api.post<{ created: number; skipped: number; structure_id: number }>(`${base}/structures/${structureId}/generate`, payload)).data;

export const studentFees = async (studentId: number) =>
  (await api.get<StudentFeeView>(`${base}/students/${studentId}`)).data;

export const collect = async (payload: {
  invoice_id: number;
  amount: number;
  method: PaymentMethod;
  reference?: string;
}) => (await api.post(`${base}/collect`, payload)).data;

export const collectionSummary = async (start: string, end: string) =>
  (await api.get<CollectionSummary>(`${base}/reports/collection`, { params: { start, end } })).data;
export const defaulterReport = async () =>
  (await api.get<DefaulterRow[]>(`${base}/reports/defaulters`)).data;
