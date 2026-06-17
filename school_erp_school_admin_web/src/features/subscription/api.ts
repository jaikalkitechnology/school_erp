import { api } from "@/lib/api";
import { n, nOrNull } from "@/lib/coerce";

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

const coerceInvoice = (i: SubscriptionInvoice): SubscriptionInvoice => ({
  ...i,
  subtotal: n(i.subtotal),
  discount_amount: n(i.discount_amount),
  tax_amount: n(i.tax_amount),
  cgst_amount: n(i.cgst_amount),
  sgst_amount: n(i.sgst_amount),
  igst_amount: n(i.igst_amount),
  total_amount: n(i.total_amount),
  paid_amount: n(i.paid_amount),
});

export const mySubscription = async () => {
  const data = (await api.get<Subscription>("/v1/school-admin/subscription")).data;
  return {
    ...data,
    monthly_price: nOrNull(data.monthly_price),
    invoices: (data.invoices ?? []).map(coerceInvoice),
  };
};
