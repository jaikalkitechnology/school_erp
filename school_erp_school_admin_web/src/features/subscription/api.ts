import { api } from "@/lib/api";

export type InvoiceStatus = "draft" | "pending" | "partial" | "paid" | "void" | "refunded";

export interface SubscriptionInvoice {
  id: number;
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
  status: InvoiceStatus;
  notes: string | null;
}

export interface Subscription {
  plan_id: number | null;
  plan_code: string | null;
  plan_name: string | null;
  monthly_price: number | null;
  subscription_start: string | null;
  subscription_end: string | null;
  status: string;
  invoices: SubscriptionInvoice[];
}

export const mySubscription = async () =>
  (await api.get<Subscription>("/v1/school-admin/subscription")).data;
