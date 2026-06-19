import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calculator, Pencil, Plus, Receipt, TrendingDown, Trash2, UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { StudentPicker } from "@/components/StudentPicker";
import { listClasses } from "@/features/setup/api";
import { listStudents } from "@/features/students/api";
import {
  collect,
  collectionSummary,
  createCategory,
  createStructure,
  defaulterReport,
  deleteCategory,
  deleteStructure,
  generateInvoiceForStudent,
  generateInvoices,
  listCategories,
  listStructures,
  studentFees,
  updateCategory,
  updateStructure,
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
  const [error, setError] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);
  // null = not editing; row = editing this row
  const [editing, setEditing] = useState<{ id: number; code: string; name: string; is_recurring: boolean } | null>(null);

  const create = useMutation({
    mutationFn: () => createCategory({ code, name, is_recurring: recurring }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-categories"] });
      setCode(""); setName(""); setError(null);
    },
    onError: (e: any) =>
      setError(e?.response?.data?.detail ?? "Could not add category"),
  });
  const update = useMutation({
    mutationFn: () =>
      updateCategory(editing!.id, {
        code: editing!.code,
        name: editing!.name,
        is_recurring: editing!.is_recurring,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-categories"] });
      setEditing(null);
      setOpError(null);
    },
    onError: (e: any) =>
      setOpError(e?.response?.data?.detail ?? "Could not update"),
  });
  const remove = useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-categories"] });
      setOpError(null);
    },
    onError: (e: any) =>
      setOpError(e?.response?.data?.detail ?? "Could not delete"),
  });

  const onDelete = (c: any) => {
    setOpError(null);
    if (window.confirm(
      `Delete category "${c.name}" (${c.code})?\n\n` +
        "Refused by the server if any structures or invoices already use it.",
    )) remove.mutate(c.id);
  };
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
            <>
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((c) => {
                const isEditing = editing?.id === c.id;
                return (
                  <li key={c.id} className="px-6 py-3 text-sm">
                    {isEditing ? (
                      <div className="grid gap-2 sm:grid-cols-[120px_1fr_auto_auto]">
                        <Input
                          value={editing!.code}
                          onChange={(e) => setEditing({ ...editing!, code: e.target.value })}
                          placeholder="Code"
                        />
                        <Input
                          value={editing!.name}
                          onChange={(e) => setEditing({ ...editing!, name: e.target.value })}
                          placeholder="Name"
                        />
                        <label className="flex items-center gap-1 text-xs">
                          <input
                            type="checkbox"
                            checked={editing!.is_recurring}
                            onChange={(e) => setEditing({ ...editing!, is_recurring: e.target.checked })}
                          />
                          recurring
                        </label>
                        <div className="flex gap-1">
                          <Button size="sm" onClick={() => update.mutate()} disabled={update.isPending}>
                            Save
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-indigo-dark">{c.name}</p>
                          <p className="text-xs font-mono text-saffron-dark">{c.code}</p>
                        </div>
                        <span className="mr-3 text-xs text-muted-foreground">
                          {c.is_recurring ? "recurring" : "one-time"}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Edit"
                          onClick={() => setEditing({
                            id: c.id,
                            code: c.code,
                            name: c.name,
                            is_recurring: c.is_recurring,
                          })}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Delete"
                          onClick={() => onDelete(c)}
                          disabled={remove.isPending}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {opError && (
              <p className="border-t bg-destructive/10 px-6 py-2 text-xs text-destructive">
                {opError}
              </p>
            )}
            </>
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
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={() => { setError(null); create.mutate(); }} disabled={!code || !name || create.isPending}>
            <Plus className="h-4 w-4" /> {create.isPending ? "Adding…" : "Add"}
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

  const [structureError, setStructureError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () =>
      createStructure({
        class_def_id: Number(classDefId),
        category_id: Number(categoryId),
        period,
        amount,
        due_day_of_month: dueDay,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-structures"] });
      setStructureError(null);
    },
    onError: (e: any) =>
      setStructureError(e?.response?.data?.detail ?? "Could not add structure"),
  });

  const [genFlash, setGenFlash] = useState<string | null>(null);
  const generate = useMutation({
    mutationFn: (structureId: number) =>
      generateInvoices(structureId, {
        period_start: periodStart,
        period_end: periodEnd,
        sibling_discount_pct: siblingPct,
        apply_sibling_discount: true,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["fee-structures"] });
      setGenFlash(`Created ${res.created}, skipped ${res.skipped}.`);
    },
    onError: (e: any) =>
      setGenFlash(`Error: ${e?.response?.data?.detail ?? "Generation failed"}`),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteStructure(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fee-structures"] }),
    onError: (e: any) =>
      setGenFlash(`Error: ${e?.response?.data?.detail ?? "Delete failed"}`),
  });

  // Per-row edit state.
  const [editingStruct, setEditingStruct] = useState<{
    id: number; amount: number; due_day_of_month: number;
  } | null>(null);
  const updateMut = useMutation({
    mutationFn: () => updateStructure(editingStruct!.id, {
      amount: editingStruct!.amount,
      due_day_of_month: editingStruct!.due_day_of_month,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fee-structures"] });
      setEditingStruct(null);
    },
    onError: (e: any) =>
      setGenFlash(`Error: ${e?.response?.data?.detail ?? "Update failed"}`),
  });

  // Per-row single-student generate state.
  const [singleStructId, setSingleStructId] = useState<number | null>(null);
  const [singleStudentId, setSingleStudentId] = useState("");
  const singleMut = useMutation({
    mutationFn: () => generateInvoiceForStudent(
      singleStructId!,
      Number(singleStudentId),
      {
        period_start: periodStart,
        period_end: periodEnd,
        sibling_discount_pct: siblingPct,
        apply_sibling_discount: true,
      },
    ),
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ["fee-structures"] });
      qc.invalidateQueries({ queryKey: ["student-fees"] });
      setGenFlash(`Invoice ${inv.invoice_number} created.`);
      setSingleStructId(null);
      setSingleStudentId("");
    },
    onError: (e: any) =>
      setGenFlash(`Error: ${e?.response?.data?.detail ?? "Could not generate"}`),
  });

  const onDeleteStruct = (s: any) => {
    if (window.confirm(
      `Delete this ${s.period} structure for ` +
      `${classMap.get(s.class_def_id) ?? "Class"}` +
      ` / ${catMap.get(s.category_id) ?? "category"}?\n\n` +
      "Refused if any invoices already exist for it.",
    )) remove.mutate(s.id);
  };

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
          {structureError && (
            <p className="col-span-5 text-sm text-destructive">{structureError}</p>
          )}
          <div className="col-span-5 flex justify-end">
            <Button
              disabled={classDefId === "" || categoryId === "" || amount <= 0 || create.isPending}
              onClick={() => { setStructureError(null); create.mutate(); }}
            >
              <Plus className="h-4 w-4" />
              {create.isPending ? "Adding…" : "Add structure"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Calculator className="h-5 w-5" /> Generate invoices</CardTitle>
          <CardDescription>
            Pick the billing period below — these dates apply to every
            <strong> Generate invoices</strong> button further down.
            Auto-applies a sibling discount when shared parent contact
            is detected.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <FieldDate label="Period start *" value={periodStart} onChange={setPeriodStart} />
          <FieldDate label="Period end *" value={periodEnd} onChange={setPeriodEnd} />
          <FieldNum label="Sibling discount %" value={siblingPct} onChange={setSiblingPct} />
        </CardContent>
        {(!periodStart || !periodEnd) && (
          <CardContent className="pt-0">
            <p className="rounded-md bg-marigold-pale/40 px-3 py-2 text-xs text-marigold-dark">
              Generate buttons stay disabled until <strong>Period start</strong>
              {" "}and <strong>Period end</strong> are both set above.
            </p>
          </CardContent>
        )}
        {genFlash && (
          <CardContent className="pt-0">
            <p
              className={cn(
                "text-sm",
                genFlash.startsWith("Error")
                  ? "text-destructive"
                  : "text-teal-dark",
              )}
            >
              {genFlash}
            </p>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader><CardTitle>Existing structures ({list.data?.length ?? 0})</CardTitle></CardHeader>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((s) => {
                const editing = editingStruct?.id === s.id;
                const opening = singleStructId === s.id;
                return (
                  <li key={s.id} className="px-6 py-3 text-sm">
                    {editing ? (
                      <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto_auto]">
                        <p className="font-medium text-indigo-dark">
                          {classMap.get(s.class_def_id) ?? `Class ${s.class_def_id}`} ·{" "}
                          {catMap.get(s.category_id) ?? `Cat ${s.category_id}`} · {s.period}
                        </p>
                        <Input
                          type="number"
                          value={editingStruct!.amount}
                          onChange={(e) => setEditingStruct({
                            ...editingStruct!,
                            amount: Number(e.target.value) || 0,
                          })}
                          className="w-28"
                          placeholder="Amount"
                        />
                        <Input
                          type="number"
                          value={editingStruct!.due_day_of_month}
                          onChange={(e) => setEditingStruct({
                            ...editingStruct!,
                            due_day_of_month: Math.max(1, Math.min(28, Number(e.target.value) || 10)),
                          })}
                          className="w-20"
                          placeholder="Due day"
                        />
                        <div className="flex gap-1">
                          <Button size="sm" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
                            Save
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditingStruct(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-indigo-dark">
                            {classMap.get(s.class_def_id) ?? `Class ${s.class_def_id}`} ·{" "}
                            {catMap.get(s.category_id) ?? `Cat ${s.category_id}`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {s.period} · ₹{Number(s.amount).toFixed(0)} · due {s.due_day_of_month}th
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => generate.mutate(s.id)}
                            disabled={!periodStart || !periodEnd || generate.isPending}
                            title={!periodStart || !periodEnd ? "Set the period dates above first" : ""}
                          >
                            Generate (all in class)
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setSingleStructId(opening ? null : s.id)}
                            disabled={!periodStart || !periodEnd}
                            title={!periodStart || !periodEnd ? "Set the period dates above first" : ""}
                          >
                            <UserPlus className="mr-1 h-3 w-3" />
                            Single student
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Edit"
                            onClick={() => setEditingStruct({
                              id: s.id,
                              amount: Number(s.amount) || 0,
                              due_day_of_month: s.due_day_of_month,
                            })}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete"
                            onClick={() => onDeleteStruct(s)}
                            disabled={remove.isPending}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {opening && (
                      <div className="mt-3 rounded-md border border-saffron-pale bg-saffron-pale/20 p-3">
                        <p className="mb-2 text-xs font-medium text-indigo-dark">
                          Generate one invoice for a specific student
                        </p>
                        <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                          <StudentPicker
                            value={singleStudentId}
                            onChange={(v) => setSingleStudentId(v)}
                          />
                          <Button
                            size="sm"
                            onClick={() => singleMut.mutate()}
                            disabled={!singleStudentId || singleMut.isPending}
                          >
                            {singleMut.isPending ? "Generating…" : "Create invoice"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setSingleStructId(null);
                              setSingleStudentId("");
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
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
                        Due {inv.due_date} · ₹{inv.total_amount.toFixed(0)} (paid ₹{inv.paid_amount.toFixed(0)})
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
