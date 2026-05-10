import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createPlan, listPlans, updatePlan } from "@/features/schools/api";
import type { PlanWrite } from "@/features/schools/api";

export function PlansPage() {
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: ["plans"], queryFn: listPlans });
  const [creating, setCreating] = useState(false);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["plans"] });
  const create = useMutation({ mutationFn: createPlan, onSuccess: () => { invalidate(); setCreating(false); } });
  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<PlanWrite> }) => updatePlan(id, payload),
    onSuccess: invalidate,
  });

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 3 · Subscription</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">Plans &amp; pricing</h1>
        </div>
        <Button onClick={() => setCreating((v) => !v)}>
          <Plus className="h-4 w-4" />
          New plan
        </Button>
      </header>

      {creating && <PlanForm onSubmit={(p) => create.mutate(p)} submitting={create.isPending} />}

      <div className="grid gap-4 lg:grid-cols-2">
        {(plans.data ?? []).map((p) => (
          <Card key={p.id} className={p.is_active ? "border-saffron-pale" : "opacity-60"}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardDescription className="font-mono text-xs uppercase tracking-wider text-saffron-dark">{p.code}</CardDescription>
                  <CardTitle>{p.name}</CardTitle>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => update.mutate({ id: p.id, payload: { is_active: !p.is_active } })}
                >
                  {p.is_active ? "Disable" : "Enable"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                <Stat label="Monthly" value={`₹${p.monthly_price}`} />
                <Stat label="Annual" value={`₹${p.annual_price}`} />
                <Stat label="Students" value={p.student_limit || "Unlimited"} />
                <Stat label="Teachers" value={p.teacher_limit || "Unlimited"} />
                <Stat label="Storage" value={`${p.storage_gb} GB`} />
                <Stat label="SMS" value={p.sms_quota.toLocaleString("en-IN")} />
              </div>
              <div className="flex flex-wrap gap-1">
                {p.modules_included?.map((m) => (
                  <span key={m} className="rounded-full border border-saffron-pale bg-saffron-pale/40 px-2 py-0.5 text-[11px] capitalize">
                    {m.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="font-medium text-indigo-dark">{value}</p>
    </div>
  );
}

function PlanForm({ onSubmit, submitting }: { onSubmit: (p: PlanWrite) => void; submitting: boolean }) {
  const [form, setForm] = useState<PlanWrite>({
    code: "",
    name: "",
    monthly_price: 0,
    annual_price: 0,
    student_limit: 0,
    teacher_limit: 0,
    storage_gb: 5,
    sms_quota: 0,
    modules_included: [],
    is_active: true,
  });
  const set = <K extends keyof PlanWrite>(k: K, v: PlanWrite[K]) => setForm((s) => ({ ...s, [k]: v }));
  return (
    <Card className="border-saffron">
      <CardHeader>
        <CardTitle>New plan</CardTitle>
        <CardDescription>Plans seed automatically per tenant on creation; change carefully.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid grid-cols-2 gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(form);
          }}
        >
          <FieldText label="Code" value={form.code} onChange={(v) => set("code", v.toLowerCase().replace(/[^a-z0-9_-]/g, ""))} required />
          <FieldText label="Name" value={form.name} onChange={(v) => set("name", v)} required />
          <FieldNum label="Monthly price (₹)" value={form.monthly_price} onChange={(v) => set("monthly_price", v)} />
          <FieldNum label="Annual price (₹)" value={form.annual_price} onChange={(v) => set("annual_price", v)} />
          <FieldNum label="Student limit (0 = unlimited)" value={form.student_limit ?? 0} onChange={(v) => set("student_limit", v)} />
          <FieldNum label="Teacher limit" value={form.teacher_limit ?? 0} onChange={(v) => set("teacher_limit", v)} />
          <FieldNum label="Storage (GB)" value={form.storage_gb ?? 5} onChange={(v) => set("storage_gb", v)} />
          <FieldNum label="SMS quota" value={form.sms_quota ?? 0} onChange={(v) => set("sms_quota", v)} />
          <div className="col-span-2 flex justify-end">
            <Button type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create plan"}</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function FieldText({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-destructive"> *</span>}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} required={required} />
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
