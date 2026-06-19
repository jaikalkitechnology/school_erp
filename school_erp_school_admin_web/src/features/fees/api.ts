import { api } from "@/lib/api";

/** Pydantic v2 serialises Decimal as a JSON *string* (e.g. "1500.00") to
 *  preserve precision. TypeScript declares these fields as `number` and
 *  React components call `.toFixed()` on them — which throws on strings.
 *  Coerce at the edge so the rest of the app keeps treating them as
 *  numbers. Returns 0 on null / undefined / NaN. */
const n = (v: unknown): number => {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const parsed = Number(v);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const numMap = (m: Record<string, unknown> | null | undefined): Record<string, number> => {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(m ?? {})) out[k] = n(v);
  return out;
};

const coerceInvoice = (i: FeeInvoice): FeeInvoice => ({
  ...i,
  base_amount: n(i.base_amount),
  discount_amount: n(i.discount_amount),
  late_fee_amount: n(i.late_fee_amount),
  total_amount: n(i.total_amount),
  paid_amount: n(i.paid_amount),
});

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
export const updateCategory = async (id: number, p: Partial<FeeCategory>) =>
  (await api.patch<FeeCategory>(`${base}/categories/${id}`, p)).data;
export const deleteCategory = async (id: number) => {
  await api.delete(`${base}/categories/${id}`);
};

export const listStructures = async (class_def_id?: number) =>
  (await api.get<FeeStructure[]>(`${base}/structures`, { params: class_def_id ? { class_def_id } : undefined })).data;
export const createStructure = async (p: Partial<FeeStructure>) =>
  (await api.post<FeeStructure>(`${base}/structures`, p)).data;
export const updateStructure = async (id: number, p: Partial<FeeStructure>) =>
  (await api.patch<FeeStructure>(`${base}/structures/${id}`, p)).data;
export const deleteStructure = async (id: number) => {
  await api.delete(`${base}/structures/${id}`);
};

export const generateInvoiceForStudent = async (
  structureId: number,
  studentId: number,
  payload: {
    period_start: string;
    period_end: string;
    sibling_discount_pct?: number;
    apply_sibling_discount?: boolean;
  },
) => (await api.post<FeeInvoice>(
  `${base}/structures/${structureId}/generate-for-student/${studentId}`,
  payload,
)).data;
export const generateInvoices = async (
  structureId: number,
  payload: {
    period_start: string;
    period_end: string;
    sibling_discount_pct?: number;
    apply_sibling_discount?: boolean;
  },
) => (await api.post<{ created: number; skipped: number; structure_id: number }>(`${base}/structures/${structureId}/generate`, payload)).data;

export const studentFees = async (studentId: number) => {
  const v = (await api.get<StudentFeeView>(`${base}/students/${studentId}`)).data;
  return {
    ...v,
    total_due: n(v.total_due),
    total_paid: n(v.total_paid),
    invoices: (v.invoices ?? []).map(coerceInvoice),
  };
};

export const collect = async (payload: {
  invoice_id: number;
  amount: number;
  method: PaymentMethod;
  reference?: string;
}) => (await api.post(`${base}/collect`, payload)).data;

export const collectionSummary = async (start: string, end: string) => {
  const s = (await api.get<CollectionSummary>(`${base}/reports/collection`, { params: { start, end } })).data;
  return {
    ...s,
    total_collected: n(s.total_collected),
    total_pending: n(s.total_pending),
    overdue_amount: n(s.overdue_amount),
    daily: (s.daily ?? []).map((d) => ({
      ...d,
      payments: n(d.payments),
      amount: n(d.amount),
    })),
    by_method: numMap(s.by_method),
    by_category: numMap(s.by_category),
  };
};

export const defaulterReport = async () => {
  const rows = (await api.get<DefaulterRow[]>(`${base}/reports/defaulters`)).data;
  return rows.map((d) => ({
    ...d,
    invoices_overdue: n(d.invoices_overdue),
    amount_overdue: n(d.amount_overdue),
  }));
};
