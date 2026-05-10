import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, RefreshCw, Plus, Send, Undo2, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listTenants, listPlans } from "@/features/schools/api";
import {
  autoRenew,
  changePlan,
  generateInvoice,
  listInvoices,
  recordPayment,
  recordRefund,
  reports,
  voidInvoice,
  type GstTreatment,
  type InvoiceStatus,
} from "./api";

const TABS = ["Reports", "Invoices", "Plan changes", "Auto-renew"] as const;
type Tab = (typeof TABS)[number];

const STATUS_TONE: Record<InvoiceStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  pending: "bg-marigold-pale text-marigold-dark",
  partial: "bg-saffron-pale text-saffron-darker",
  paid: "bg-teal-pale text-teal-dark",
  void: "bg-muted text-muted-foreground line-through",
  refunded: "bg-destructive/15 text-destructive",
};

export function BillingPage() {
  const [tab, setTab] = useState<Tab>("Reports");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 21 · Subscription billing
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Billing</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Generate per-tenant invoices with GST split (CGST+SGST or IGST), record
          payments and refunds, change plans with proration, and bulk auto-renew
          subscriptions.
        </p>
      </header>
      <nav className="flex gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label
                ? "border-b-2 border-saffron text-saffron-darker"
                : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "Reports" && <ReportsPanel />}
      {tab === "Invoices" && <InvoicesPanel />}
      {tab === "Plan changes" && <PlanChangesPanel />}
      {tab === "Auto-renew" && <AutoRenewPanel />}
    </div>
  );
}

// ---- Reports -----------------------------------------------------------

function ReportsPanel() {
  const { data } = useQuery({ queryKey: ["billing-reports"], queryFn: reports });
  if (!data) return null;
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <Tile label="Total billed" value={`₹${data.total_billed}`} />
      <Tile label="Collected" value={`₹${data.total_collected}`} tone="teal" />
      <Tile label="Pending" value={`₹${data.pending}`} tone="marigold" />
      <Tile label="Refunded" value={`₹${data.refunded}`} tone="destructive" />
      <Tile label="Overdue invoices" value={data.overdue_count} tone="destructive" />
      <Tile label="MRR" value={`₹${data.mrr}`} tone="saffron" />
      <Tile label="ARR" value={`₹${data.arr}`} tone="saffron" />
    </div>
  );
}

// ---- Invoices ----------------------------------------------------------

function InvoicesPanel() {
  const qc = useQueryClient();
  const { data: schools = [] } = useQuery({ queryKey: ["schools"], queryFn: () => listTenants() });
  const [tenantFilter, setTenantFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");
  const { data: invoices = [] } = useQuery({
    queryKey: ["billing-invoices", tenantFilter, statusFilter],
    queryFn: () =>
      listInvoices({
        tenant_id: tenantFilter ? Number(tenantFilter) : undefined,
        status_filter: statusFilter || undefined,
      }),
  });

  const today = new Date().toISOString().slice(0, 10);
  const monthEnd = (() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 1);
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  })();
  const [formTenant, setFormTenant] = useState("");
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(monthEnd);
  const [gstRate, setGstRate] = useState("18");
  const [treatment, setTreatment] = useState<GstTreatment>("intra");
  const [place, setPlace] = useState("");

  const create = useMutation({
    mutationFn: () =>
      generateInvoice({
        tenant_id: Number(formTenant),
        period_start: start,
        period_end: end,
        gst_rate_pct: Number(gstRate),
        gst_treatment: treatment,
        place_of_supply: place || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-invoices"] });
      qc.invalidateQueries({ queryKey: ["billing-reports"] });
    },
  });

  const [payInvoice, setPayInvoice] = useState<number | null>(null);
  const [payAmount, setPayAmount] = useState("");
  const pay = useMutation({
    mutationFn: () =>
      recordPayment({
        invoice_id: payInvoice!,
        amount: Number(payAmount),
        method: "bank_transfer",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing-invoices"] });
      qc.invalidateQueries({ queryKey: ["billing-reports"] });
      setPayInvoice(null);
      setPayAmount("");
    },
  });

  const refund = useMutation({
    mutationFn: ({ id, amount }: { id: number; amount: number }) =>
      recordRefund({ invoice_id: id, amount }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-invoices"] }),
  });

  const voidIt = useMutation({
    mutationFn: (id: number) => voidInvoice(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-invoices"] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Generate invoice</CardTitle>
          <CardDescription>Subtotal = monthly_price × (period days / 30). GST split applied.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3 md:grid-cols-6">
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={formTenant}
            onChange={(e) => setFormTenant(e.target.value)}
          >
            <option value="">Tenant</option>
            {schools.map((s) => (
              <option key={s.id} value={s.id}>{s.school_name}</option>
            ))}
          </select>
          <Input value={start} onChange={(e) => setStart(e.target.value)} />
          <Input value={end} onChange={(e) => setEnd(e.target.value)} />
          <Input placeholder="GST %" value={gstRate} onChange={(e) => setGstRate(e.target.value)} />
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={treatment}
            onChange={(e) => setTreatment(e.target.value as GstTreatment)}
          >
            <option value="intra">Intra-state (CGST+SGST)</option>
            <option value="inter">Inter-state (IGST)</option>
            <option value="exempt">Exempt</option>
          </select>
          <Button onClick={() => create.mutate()} disabled={!formTenant || create.isPending}>
            <Plus className="mr-1 h-4 w-4" />
            Invoice
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Invoices</CardTitle>
            <CardDescription>{invoices.length} rows</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={tenantFilter}
              onChange={(e) => setTenantFilter(e.target.value)}
            >
              <option value="">All tenants</option>
              {schools.map((s) => (
                <option key={s.id} value={s.id}>{s.school_name}</option>
              ))}
            </select>
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | "")}
            >
              <option value="">All status</option>
              <option value="pending">Pending</option>
              <option value="partial">Partial</option>
              <option value="paid">Paid</option>
              <option value="void">Void</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Invoice #</th>
                <th>Tenant</th>
                <th>Period</th>
                <th>Total</th>
                <th>Paid</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((i) => {
                const tenantName =
                  schools.find((s) => s.id === i.tenant_id)?.school_name ?? `#${i.tenant_id}`;
                const balance = Number(i.total_amount) - Number(i.paid_amount);
                return (
                  <tr key={i.id} className="border-t border-saffron-pale align-top">
                    <td className="py-2 font-mono text-xs">{i.invoice_number}</td>
                    <td>{tenantName}</td>
                    <td className="text-xs text-muted-foreground">
                      {i.period_start} → {i.period_end}
                    </td>
                    <td>₹{i.total_amount}</td>
                    <td>₹{i.paid_amount}</td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", STATUS_TONE[i.status])}>
                        {i.status}
                      </span>
                    </td>
                    <td className="space-x-1 text-right">
                      {i.status === "pending" || i.status === "partial" ? (
                        <Button size="sm" variant="ghost" onClick={() => {
                          setPayInvoice(i.id);
                          setPayAmount(balance.toFixed(2));
                        }}>
                          <Send className="mr-1 h-3 w-3" />
                          Pay
                        </Button>
                      ) : null}
                      {i.status === "paid" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => refund.mutate({ id: i.id, amount: Number(i.paid_amount) - Number(i.refunded_amount) })}
                        >
                          <Undo2 className="mr-1 h-3 w-3" />
                          Refund
                        </Button>
                      )}
                      {i.status !== "paid" && i.status !== "void" && i.status !== "refunded" && (
                        <Button size="sm" variant="ghost" onClick={() => voidIt.mutate(i.id)}>
                          <Ban className="mr-1 h-3 w-3" />
                          Void
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {payInvoice !== null && (
            <div className="mt-3 flex items-center gap-2 rounded border border-saffron-pale bg-saffron-pale/30 p-3">
              <span className="text-sm">Pay invoice #{payInvoice}</span>
              <Input
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                className="w-32"
              />
              <Button onClick={() => pay.mutate()} disabled={pay.isPending || !payAmount}>
                Record
              </Button>
              <Button variant="ghost" onClick={() => setPayInvoice(null)}>
                Cancel
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Plan changes ------------------------------------------------------

function PlanChangesPanel() {
  const qc = useQueryClient();
  const { data: schools = [] } = useQuery({ queryKey: ["schools"], queryFn: () => listTenants() });
  const { data: plans = [] } = useQuery({ queryKey: ["plans"], queryFn: () => listPlans() });
  const [tenantId, setTenantId] = useState("");
  const [planId, setPlanId] = useState("");
  const [proRate, setProRate] = useState(true);
  const today = new Date().toISOString().slice(0, 10);
  const [effective, setEffective] = useState(today);
  const [flash, setFlash] = useState<string | null>(null);

  const change = useMutation({
    mutationFn: () =>
      changePlan({
        tenant_id: Number(tenantId),
        new_plan_id: Number(planId),
        effective_on: effective,
        pro_rate: proRate,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["billing-invoices"] });
      qc.invalidateQueries({ queryKey: ["schools"] });
      setFlash(
        `Plan changed. Pro-rated charge: ₹${res.pro_rated_charge}, days remaining: ${res.days_remaining}, invoice: ${res.invoice_id ?? "—"}`,
      );
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upgrade / downgrade</CardTitle>
        <CardDescription>If pro-rate is on, the diff for remaining days is invoiced at the new rate.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <div>
          <Label>Tenant</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
          >
            <option value="">Select…</option>
            {schools.map((s) => (
              <option key={s.id} value={s.id}>{s.school_name}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>New plan</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
          >
            <option value="">Select…</option>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>{p.name} (₹{p.monthly_price}/mo)</option>
            ))}
          </select>
        </div>
        <div>
          <Label>Effective</Label>
          <Input value={effective} onChange={(e) => setEffective(e.target.value)} />
        </div>
        <div className="flex items-end gap-2">
          <input
            id="pro-rate"
            type="checkbox"
            checked={proRate}
            onChange={(e) => setProRate(e.target.checked)}
          />
          <Label htmlFor="pro-rate">Pro-rate</Label>
        </div>
        <div className="flex items-end">
          <Button
            onClick={() => change.mutate()}
            disabled={!tenantId || !planId || change.isPending}
          >
            <RefreshCw className="mr-1 h-4 w-4" />
            Apply
          </Button>
        </div>
        {flash && (
          <div className="col-span-full rounded bg-teal-pale p-2 text-sm text-teal-dark">
            {flash}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---- Auto-renew --------------------------------------------------------

function AutoRenewPanel() {
  const qc = useQueryClient();
  const [months, setMonths] = useState("1");
  const [days, setDays] = useState("14");
  const [gst, setGst] = useState("18");
  const [flash, setFlash] = useState<string | null>(null);
  const run = useMutation({
    mutationFn: () =>
      autoRenew({
        period_months: Number(months) || 1,
        due_in_days: Number(days) || 14,
        gst_rate_pct: Number(gst) || 18,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["billing-invoices"] });
      qc.invalidateQueries({ queryKey: ["billing-reports"] });
      setFlash(`Generated ${res.generated}, skipped ${res.skipped}`);
    },
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Bulk renew</CardTitle>
        <CardDescription>
          Picks every active tenant whose subscription expires within the window and
          generates a fresh invoice for the next period. Idempotent on re-run.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <Label>Months</Label>
          <Input value={months} onChange={(e) => setMonths(e.target.value)} />
        </div>
        <div>
          <Label>Due in days</Label>
          <Input value={days} onChange={(e) => setDays(e.target.value)} />
        </div>
        <div>
          <Label>GST %</Label>
          <Input value={gst} onChange={(e) => setGst(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button onClick={() => run.mutate()} disabled={run.isPending}>
            <FileText className="mr-1 h-4 w-4" />
            Run
          </Button>
        </div>
        {flash && (
          <div className="col-span-full text-sm text-teal-dark">{flash}</div>
        )}
      </CardContent>
    </Card>
  );
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "teal" | "marigold" | "saffron" | "destructive";
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 font-display text-2xl",
            tone === "teal" && "text-teal-dark",
            tone === "marigold" && "text-marigold-dark",
            tone === "saffron" && "text-saffron-darker",
            tone === "destructive" && "text-destructive",
            !tone && "text-indigo-dark",
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
