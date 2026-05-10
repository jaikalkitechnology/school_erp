import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { createTenant, listPlans } from "./api";
import type { CreateTenantPayload } from "./types";

type Step = {
  id: string;
  title: string;
  description: string;
};

const STEPS: Step[] = [
  { id: "info", title: "School Information", description: "Identity, address, contact." },
  { id: "plan", title: "Subscription Plan", description: "Pick a plan; trial starts immediately." },
  { id: "branding", title: "Branding", description: "Colors and logo URL." },
  { id: "academic", title: "Academic Setup", description: "Affiliation, medium." },
  { id: "admin", title: "Admin Account", description: "Created in Phase 2 seed; left as placeholder here." },
  { id: "modules", title: "Modules", description: "Modules included with the plan." },
  { id: "review", title: "Review & Launch", description: "Confirm and create the tenant." },
];

interface FormState {
  school_name: string;
  school_code: string;
  subdomain: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  affiliation_board: string;
  medium: string;
  primary_color: string;
  secondary_color: string;
  plan_code: string;
}

const INITIAL: FormState = {
  school_name: "",
  school_code: "",
  subdomain: "",
  city: "",
  state: "",
  pincode: "",
  phone: "",
  email: "",
  affiliation_board: "CBSE",
  medium: "English",
  primary_color: "#E85D2E",
  secondary_color: "#0F766E",
  plan_code: "standard",
};

export function OnboardingWizard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: ["plans"], queryFn: listPlans });
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(
    () => plans.data?.find((p) => p.code === form.plan_code),
    [plans.data, form.plan_code],
  );

  const mutation = useMutation({
    mutationFn: (payload: CreateTenantPayload) => createTenant(payload),
    onSuccess: (tenant) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      navigate(`/schools/${tenant.id}`);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not create the school"),
  });

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((s) => ({ ...s, [key]: value }));

  const canAdvance = (() => {
    if (stepIndex === 0) return form.school_name.length > 1 && form.school_code.length > 1 && /^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(form.subdomain);
    if (stepIndex === 1) return Boolean(form.plan_code);
    return true;
  })();

  const submit = () => {
    setError(null);
    mutation.mutate({
      school_name: form.school_name,
      school_code: form.school_code,
      subdomain: form.subdomain,
      plan_code: form.plan_code,
      city: form.city || undefined,
      state: form.state || undefined,
      affiliation_board: form.affiliation_board || undefined,
      medium: form.medium || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 3</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">
          Onboard a <em className="italic text-saffron">new school</em>.
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Seven steps. Trial starts the moment you finish.
        </p>
      </header>

      <div className="grid grid-cols-[260px_1fr] gap-6">
        <ol className="space-y-1 rounded-lg border border-saffron-pale bg-warm-white p-3">
          {STEPS.map((step, i) => {
            const completed = i < stepIndex;
            const active = i === stepIndex;
            return (
              <li
                key={step.id}
                className={cn(
                  "flex items-start gap-3 rounded-md px-3 py-2 text-sm",
                  active && "bg-saffron-pale text-saffron-darker",
                  completed && "text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-mono",
                    active ? "bg-saffron text-warm-white" : completed ? "bg-teal text-warm-white" : "bg-muted text-muted-foreground",
                  )}
                >
                  {completed ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                <span>
                  <span className="block font-medium">{step.title}</span>
                  <span className="block text-xs text-muted-foreground">{step.description}</span>
                </span>
              </li>
            );
          })}
        </ol>

        <Card>
          <CardHeader>
            <CardTitle>{STEPS[stepIndex].title}</CardTitle>
            <CardDescription>{STEPS[stepIndex].description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {stepIndex === 0 && (
              <div className="grid grid-cols-2 gap-4">
                <Field label="School name" value={form.school_name} onChange={(v) => set("school_name", v)} required />
                <Field label="School code" value={form.school_code} onChange={(v) => set("school_code", v)} required />
                <Field label="Subdomain" value={form.subdomain} onChange={(v) => set("subdomain", v.toLowerCase())} required hint="lowercase, hyphens ok; will become subdomain.jaikalki.com" />
                <Field label="Phone" value={form.phone} onChange={(v) => set("phone", v)} />
                <Field label="Email" value={form.email} onChange={(v) => set("email", v)} />
                <Field label="City" value={form.city} onChange={(v) => set("city", v)} />
                <Field label="State" value={form.state} onChange={(v) => set("state", v)} />
                <Field label="PIN" value={form.pincode} onChange={(v) => set("pincode", v)} />
              </div>
            )}

            {stepIndex === 1 && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  {(plans.data ?? []).map((p) => (
                    <button
                      key={p.code}
                      type="button"
                      onClick={() => set("plan_code", p.code)}
                      className={cn(
                        "rounded-lg border p-4 text-left transition-colors",
                        form.plan_code === p.code
                          ? "border-saffron bg-saffron-pale"
                          : "border-border hover:border-saffron-light",
                      )}
                    >
                      <p className="text-xs uppercase tracking-wider text-saffron-dark">{p.code}</p>
                      <p className="mt-1 text-lg font-display text-indigo-dark">{p.name}</p>
                      <p className="text-2xl font-mono text-indigo-dark">₹{p.monthly_price}/mo</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {p.student_limit ? `${p.student_limit} students` : "Unlimited students"} · {p.storage_gb}GB
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {stepIndex === 2 && (
              <div className="grid grid-cols-2 gap-4">
                <Field label="Primary colour" value={form.primary_color} onChange={(v) => set("primary_color", v)} />
                <Field label="Secondary colour" value={form.secondary_color} onChange={(v) => set("secondary_color", v)} />
                <div className="col-span-2 flex items-center gap-3">
                  <span className="block h-12 w-24 rounded-md" style={{ background: form.primary_color }} />
                  <span className="block h-12 w-24 rounded-md" style={{ background: form.secondary_color }} />
                  <p className="text-xs text-muted-foreground">Logo upload lands in Phase 4 (school admin).</p>
                </div>
              </div>
            )}

            {stepIndex === 3 && (
              <div className="grid grid-cols-2 gap-4">
                <Field label="Affiliation board" value={form.affiliation_board} onChange={(v) => set("affiliation_board", v)} hint="CBSE / ICSE / State / IB" />
                <Field label="Medium" value={form.medium} onChange={(v) => set("medium", v)} hint="English / Hindi / Marathi / Tamil…" />
              </div>
            )}

            {stepIndex === 4 && (
              <div className="rounded-md border border-dashed border-saffron-pale bg-saffron-pale/40 p-4 text-sm text-indigo-dark">
                The school admin user is created automatically the first time the school admin signs in via OTP.
                For now Phase 2 seeds <code className="font-mono">admin@demo.school / School@123</code> for the demo tenant.
              </div>
            )}

            {stepIndex === 5 && selectedPlan && (
              <ul className="grid grid-cols-2 gap-2 text-sm">
                {selectedPlan.modules_included?.length ? (
                  selectedPlan.modules_included.map((m) => (
                    <li key={m} className="flex items-center gap-2 rounded-md border border-saffron-pale px-3 py-2">
                      <Check className="h-4 w-4 text-teal" />
                      <span className="capitalize">{m.replace(/_/g, " ")}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-muted-foreground">Modules ship with the plan and can be toggled per-school in Phase 3.8.</li>
                )}
              </ul>
            )}

            {stepIndex === 6 && (
              <ReviewBlock form={form} planName={selectedPlan?.name ?? form.plan_code} />
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex justify-between border-t border-saffron-pale pt-4">
              <Button
                variant="ghost"
                disabled={stepIndex === 0}
                onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                Back
              </Button>
              {stepIndex < STEPS.length - 1 ? (
                <Button disabled={!canAdvance} onClick={() => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1))}>
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={submit} disabled={mutation.isPending}>
                  {mutation.isPending ? "Launching…" : "Launch school"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-destructive"> *</span>}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ReviewBlock({ form, planName }: { form: FormState; planName: string }) {
  const rows = [
    ["School", form.school_name],
    ["Code", form.school_code],
    ["Subdomain", `${form.subdomain}.jaikalki.com`],
    ["Plan", planName],
    ["Affiliation", form.affiliation_board],
    ["Medium", form.medium],
    ["Location", [form.city, form.state].filter(Boolean).join(", ") || "—"],
    ["Contact", [form.phone, form.email].filter(Boolean).join(" · ") || "—"],
    ["Branding", `${form.primary_color} / ${form.secondary_color}`],
  ] as const;
  return (
    <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-saffron-pale pb-2">
          <dt className="text-muted-foreground">{k}</dt>
          <dd className="text-right font-medium text-indigo-dark">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
