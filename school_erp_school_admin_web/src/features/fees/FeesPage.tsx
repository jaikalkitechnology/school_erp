import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calculator, Plus, Receipt, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses } from "@/features/setup/api";
import { listStudents } from "@/features/students/api";
import {
  collect,
  collectionSummary,
  createCategory,
  createStructure,
  defaulterReport,
  generateInvoices,
  listCategories,
  listStructures,
  studentFees,
  type FeePeriod,
  type InvoiceStatus,
  type PaymentMethod,
} from "./api";

const STATUS_TONE: Record<InvoiceStatus, string> = {
  pending: "bg-marigold-pale text-marigold-dark",
  partial: "bg-saffron-pale text-saffron-darker",
  paid: "bg-teal-pale text-teal-dark",
  overdue: "bg-destructive/15 text-destructive",
  waived: "bg-muted text-muted-foreground",
  cancelled: "bg-muted text-muted-foreground",
};

const TABS = ["Categories", "Structures", "Collection", "Reports"] as const;
type Tab = (typeof TABS)[number];

export function FeesPage() {
  const [tab, setTab] = useState<Tab>("Categories");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 11 · Fees</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Fee management</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Define categories + structures, generate invoices, collect cash + UPI, and surface
          collection / defaulter reports.
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
              tab === label ? "border-b-2 border-saffron text-saffron-darker" : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "Categories" && <CategoriesPanel />}
      {tab === "Structures" && <StructuresPanel />}
      {tab === "Collection" && <CollectionPanel />}
      {tab === "Reports" && <ReportsPanel />}
    </div>
  );
}

// ---- Categories -----------------------------------------------------------

function CategoriesPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["fee-categories"], queryFn: listCategories });
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [recurring, setRecurring] = useState(true);
  const create = useMutation({
    mutationFn: () => createCategory({ code, name, is_recurring: recurring }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-categories"] });
      setCode(""); setName("");
    },
  });
  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Categories</CardTitle>
          <CardDescription>Tuition, transport, lab, hostel, library …</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : !list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Add your first category on the right.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((c) => (
                <li key={c.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium text-indigo-dark">{c.name}</p>
                    <p className="text-xs font-mono text-saffron-dark">{c.code}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">{c.is_recurring ? "recurring" : "one-time"}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Add category</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Field label="Code" value={code} onChange={setCode} placeholder="TUITION" />
          <Field label="Name" value={name} onChange={setName} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={recurring} onChange={(e) => setRecurring(e.target.checked)} className="h-4 w-4 accent-saffron" />
            Recurring (monthly / quarterly / annual)
          </label>
          <Button onClick={() => create.mutate()} disabled={!code || !name || create.isPending}>
            <Plus className="h-4 w-4" /> Add
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Structures -----------------------------------------------------------

function StructuresPanel() {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const cats = useQuery({ queryKey: ["fee-categories"], queryFn: listCategories });
  const list = useQuery({ queryKey: ["fee-structures"], queryFn: () => listStructures() });

  const [classDefId, setClassDefId] = useState<number | "">("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [period, setPeriod] = useState<FeePeriod>("monthly");
  const [amount, setAmount] = useState(0);
  const [dueDay, setDueDay] = useState(10);

  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [siblingPct, setSiblingPct] = useState(10);

  const create = useMutation({
    mutationFn: () =>
      createStructure({
        class_def_id: Number(classDefId),
        category_id: Number(categoryId),
        period,
        amount,
        due_day_of_month: dueDay,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fee-structures"] }),
  });

  const generate = useMutation({
    mutationFn: (structureId: number) =>
      generateInvoices(structureId, {
        period_start: periodStart,
        period_end: periodEnd,
        sibling_discount_pct: siblingPct,
        apply_sibling_discount: true,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fee-structures"] }),
  });

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );
  const catMap = useMemo(
    () => new Map((cats.data ?? []).map((c) => [c.id, c.name])),
    [cats.data],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>New structure</CardTitle></CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-5">
          <Select label="Class" value={classDefId} onChange={(v) => setClassDefId(v ? Number(v) : "")} options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))} />
          <Select label="Category" value={categoryId} onChange={(v) => setCategoryId(v ? Number(v) : "")} options={(cats.data ?? []).map((c) => ({ value: c.id, label: c.name }))} />
          <Select label="Period" value={period} onChange={(v) => setPeriod(v as FeePeriod)} options={[
            { value: "monthly", label: "Monthly" },
            { value: "quarterly", label: "Quarterly" },
            { value: "annual", label: "Annual" },
            { value: "one_time", label: "One-time" },
          ]} />
          <FieldNum label="Amount (₹)" value={amount} onChange={setAmount} />
          <FieldNum label="Due day" value={dueDay} onChange={setDueDay} />
          <div className="col-span-5 flex justify-end">
            <Button disabled={classDefId === "" || categoryId === "" || amount <= 0 || create.isPending} onClick={() => create.mutate()}>
              <Plus className="h-4 w-4" /> Add structure
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Calculator className="h-5 w-5" /> Generate invoices</CardTitle>
          <CardDescription>Auto-applies a sibling discount when shared parent contact is detected.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <FieldDate label="Period start" value={periodStart} onChange={setPeriodStart} />
          <FieldDate label="Period end" value={periodEnd} onChange={setPeriodEnd} />
          <FieldNum label="Sibling discount %" value={siblingPct} onChange={setSiblingPct} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Existing structures ({list.data?.length ?? 0})</CardTitle></CardHeader>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((s) => (
                <li key={s.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium text-indigo-dark">
                      {classMap.get(s.class_def_id) ?? `Class ${s.class_def_id}`} · {catMap.get(s.category_id) ?? `Cat ${s.category_id}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {s.period} · ₹{s.amount} · due {s.due_day_of_month}th
                    </p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => generate.mutate(s.id)} disabled={!periodStart || !periodEnd || generate.isPending}>
                    Generate invoices
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Collection -----------------------------------------------------------

function CollectionPanel() {
  const qc = useQueryClient();
  const students = useQuery({ queryKey: ["students-for-fees"], queryFn: () => listStudents({ status: "active", limit: 200 }) });
  const [studentId, setStudentId] = useState<number | "">("");
  const view = useQuery({
    queryKey: ["student-fees", studentId],
    queryFn: () => studentFees(Number(studentId)),
    enabled: studentId !== "",
  });

  const [amount, setAmount] = useState(0);
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [invoiceId, setInvoiceId] = useState<number | "">("");

  const collectMut = useMutation({
    mutationFn: () => collect({ invoice_id: Number(invoiceId), amount, method }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["student-fees", studentId] });
      setAmount(0);
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Pick a student</CardTitle></CardHeader>
        <CardContent>
          <select className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm" value={studentId} onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">— pick a student —</option>
            {(students.data?.items ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.full_name} · {s.admission_number}</option>
            ))}
          </select>
        </CardContent>
      </Card>

      {view.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{view.data.full_name}</CardTitle>
              <CardDescription>
                Total due ₹{view.data.total_due.toFixed(0)} · paid ₹{view.data.total_paid.toFixed(0)} · {view.data.overdue_count} overdue
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y divide-saffron-pale">
                {view.data.invoices.map((inv) => (
                  <li
                    key={inv.id}
                    className={cn(
                      "flex items-center justify-between px-6 py-3 text-sm cursor-pointer",
                      invoiceId === inv.id && "bg-saffron-pale/40",
                    )}
                    onClick={() => setInvoiceId(inv.id)}
                  >
                    <div>
                      <p className="font-medium text-indigo-dark">{inv.invoice_number}</p>
                      <p className="text-xs text-muted-foreground">
                        Due {inv.due_date} · ₹{inv.total_amount} (paid ₹{inv.paid_amount})
                      </p>
                    </div>
                    <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wider", STATUS_TONE[inv.status])}>
                      {inv.status}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Receipt className="h-5 w-5" /> Record payment</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 lg:grid-cols-3">
              <FieldNum label="Amount (₹)" value={amount} onChange={setAmount} />
              <Select label="Method" value={method} onChange={(v) => setMethod(v as PaymentMethod)} options={[
                { value: "cash", label: "Cash" },
                { value: "upi", label: "UPI" },
                { value: "card", label: "Card" },
                { value: "netbanking", label: "Net Banking" },
                { value: "cheque", label: "Cheque" },
                { value: "bank_transfer", label: "Bank Transfer" },
              ]} />
              <div className="flex items-end justify-end">
                <Button onClick={() => collectMut.mutate()} disabled={invoiceId === "" || amount <= 0 || collectMut.isPending}>
                  Collect
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// ---- Reports --------------------------------------------------------------

function ReportsPanel() {
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(today);
  const summary = useQuery({ queryKey: ["fee-summary", start, end], queryFn: () => collectionSummary(start, end) });
  const defaulters = useQuery({ queryKey: ["fee-defaulters"], queryFn: defaulterReport });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Collection window</CardTitle></CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <FieldDate label="From" value={start} onChange={setStart} />
          <FieldDate label="To" value={end} onChange={setEnd} />
        </CardContent>
      </Card>
      {summary.data && (
        <div className="grid gap-3 lg:grid-cols-3">
          <Tile label="Collected" value={`₹${summary.data.total_collected.toFixed(0)}`} hint={`${summary.data.daily.length} days w/ activity`} />
          <Tile label="Pending" value={`₹${summary.data.total_pending.toFixed(0)}`} hint="Across all open invoices" />
          <Tile label="Overdue" value={`₹${summary.data.overdue_amount.toFixed(0)}`} hint="Past due date" tone="destructive" />
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><TrendingDown className="h-5 w-5" /> Defaulters</CardTitle>
          <CardDescription>Students with overdue balances right now.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!defaulters.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No defaulters.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Student</th>
                  <th className="px-4 py-3">Invoices</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {defaulters.data.map((d) => (
                  <tr key={d.student_id} className="border-b last:border-b-0">
                    <td className="px-6 py-2">
                      <p className="font-medium text-indigo-dark">{d.full_name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{d.admission_number}</p>
                    </td>
                    <td className="px-4 py-2 font-mono">{d.invoices_overdue}</td>
                    <td className="px-4 py-2 text-right font-mono text-destructive">₹{d.amount_overdue.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- shared bits ----------------------------------------------------------

function Tile({ label, value, hint, tone }: { label: string; value: string; hint: string; tone?: "destructive" }) {
  return (
    <Card className={cn("border-saffron-pale", tone === "destructive" && "border-destructive/30")}>
      <CardHeader className="pb-2">
        <CardDescription className="text-[11px] uppercase tracking-[0.18em] text-saffron-dark">{label}</CardDescription>
        <CardTitle className={cn("text-3xl", tone === "destructive" && "text-destructive")}>{value}</CardTitle>
      </CardHeader>
      <CardContent><p className="text-xs text-muted-foreground">{hint}</p></CardContent>
    </Card>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function FieldNum({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="number" value={value} onChange={(e) => onChange(Number(e.target.value) || 0)} />
    </div>
  );
}

function FieldDate({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="date" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Select<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T | "";
  onChange: (v: string) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm" value={String(value)} onChange={(e) => onChange(e.target.value)}>
        <option value="">— pick —</option>
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
