import { api } from "@/lib/api";

export type InvoiceStatus = "draft" | "pending" | "partial" | "paid" | "void" | "refunded";
export type PaymentMethod = "bank_transfer" | "upi" | "razorpay" | "credit_note" | "other";
export type GstTreatment = "intra" | "inter" | "exempt";

export interface BillingInvoice {
  id: number;
  tenant_id: number;
  plan_id: number | null;
  invoice_number: string;
  period_start: string;
  period_end: string;
  issued_on: string;
  due_date: string;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_amount: number;
  paid_amount: number;
  refunded_amount: number;
  gst_treatment: GstTreatment;
  place_of_supply: string | null;
  notes: string | null;
  status: InvoiceStatus;
}

export interface BillingPayment {
  id: number;
  invoice_id: number;
  amount: number;
  method: PaymentMethod;
  status: string;
  reference: string | null;
  received_on: string;
  notes: string | null;
}

export interface BillingRefund {
  id: number;
  invoice_id: number;
  amount: number;
  reason: string | null;
  refunded_on: string;
}

export interface BillingReports {
  total_billed: number;
  total_collected: number;
  pending: number;
  refunded: number;
  overdue_count: number;
  mrr: number;
  arr: number;
}

const base = "/admin/billing";

export const listInvoices = async (params: { tenant_id?: number; status_filter?: InvoiceStatus } = {}) =>
  (await api.get<BillingInvoice[]>(`${base}/invoices`, { params })).data;

export const getInvoice = async (id: number) =>
  (await api.get<BillingInvoice>(`${base}/invoices/${id}`)).data;

export const generateInvoice = async (p: {
  tenant_id: number;
  plan_id?: number;
  period_start: string;
  period_end: string;
  due_date?: string;
  discount_amount?: number;
  gst_rate_pct?: number;
  gst_treatment?: GstTreatment;
  place_of_supply?: string;
  notes?: string;
}) => (await api.post<BillingInvoice>(`${base}/invoices`, p)).data;

export const voidInvoice = async (id: number) =>
  (await api.post<BillingInvoice>(`${base}/invoices/${id}/void`)).data;

export const autoRenew = async (p: { period_months?: number; due_in_days?: number; gst_rate_pct?: number }) =>
  (await api.post<{ generated: number; skipped: number; invoice_ids: number[] }>(`${base}/auto-renew`, p)).data;

export const listPayments = async (invoiceId: number) =>
  (await api.get<BillingPayment[]>(`${base}/invoices/${invoiceId}/payments`)).data;

export const recordPayment = async (p: {
  invoice_id: number; amount: number; method?: PaymentMethod; reference?: string; notes?: string;
}) => (await api.post<BillingPayment>(`${base}/payments`, p)).data;

export const recordRefund = async (p: {
  invoice_id: number; amount: number; reason?: string;
}) => (await api.post<BillingRefund>(`${base}/refunds`, p)).data;

export const changePlan = async (p: {
  tenant_id: number; new_plan_id: number; effective_on?: string; pro_rate?: boolean;
}) => (await api.post<{
  invoice_id: number | null;
  pro_rated_charge: number;
  days_remaining: number;
  old_plan_id: number | null;
  new_plan_id: number;
}>(`${base}/plan-change`, p)).data;

export const reports = async () => (await api.get<BillingReports>(`${base}/reports`)).data;
