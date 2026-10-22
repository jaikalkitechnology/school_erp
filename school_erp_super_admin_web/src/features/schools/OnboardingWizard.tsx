import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronLeft, ChevronRight, ImageUp, School, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { createTenant, listPlans, uploadTenantLogo } from "./api";
import { ColorField, HEX } from "./ColorField";
import { LocationFields } from "./LocationFields";
import type { CreateTenantPayload } from "./types";

type Step = {
  id: string;
  title: string;
  description: string;
};

const STEPS: Step[] = [
  { id: "info", title: "School Information", description: "Identity, address, contact." },
  { id: "plan", title: "Subscription Plan", description: "Pick a plan; trial starts immediately." },
  { id: "branding", title: "Branding", description: "Colors and logo." },
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

const EMAIL = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const LOGO_TYPES = ["image/png", "image/jpeg", "image/svg+xml"];
const LOGO_MAX_MB = 10; // matches the backend upload limit

export function OnboardingWizard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: ["plans"], queryFn: listPlans });
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [error, setError] = useState<string | null>(null);

  // Profile image: picked here, previewed locally, uploaded into the new
  // school's own storage right after the school is created.
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [logoError, setLogoError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<number | null>(null);
  useEffect(() => () => {
    if (logoUrl) URL.revokeObjectURL(logoUrl);
  }, [logoUrl]);

  const pickLogo = (file: File) => {
    const okType = LOGO_TYPES.includes(file.type) || /\.(png|jpe?g|svg)$/i.test(file.name);
    if (!okType) {
      setLogoError("Use a PNG, JPG or SVG image.");
      return;
    }
    if (file.size > LOGO_MAX_MB * 1024 * 1024) {
      setLogoError(`The image is larger than ${LOGO_MAX_MB} MB. Pick a smaller one.`);
      return;
    }
    setLogoError(null);
    setLogoFile(file);
    setLogoUrl(URL.createObjectURL(file));
  };
  const clearLogo = () => {
    setLogoFile(null);
    setLogoUrl(null);
    setLogoError(null);
  };

  const selectedPlan = useMemo(
    () => plans.data?.find((p) => p.code === form.plan_code),
    [plans.data, form.plan_code],
  );

  const mutation = useMutation({
    mutationFn: async (payload: CreateTenantPayload) => {
      const tenant = await createTenant(payload);
      let logoFailed: string | null = null;
      if (logoFile) {
        try {
          await uploadTenantLogo(tenant.id, logoFile);
        } catch (err: any) {
          const d = err?.response?.data?.detail;
          logoFailed = typeof d === "string" ? d : "upload failed";
        }
      }
      return { tenant, logoFailed };
    },
    onSuccess: ({ tenant, logoFailed }) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      if (logoFailed) {
        // The school exists; don't let a second click create it again.
        setCreatedId(tenant.id);
        setError(
          `School created, but the profile image couldn't be uploaded (${logoFailed}). ` +
            "The school's admin can add it later in School Profile.",
        );
        return;
      }
      navigate(`/schools/${tenant.id}`);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not create the school"),
  });

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((s) => ({ ...s, [key]: value }));

  // Optional contact fields are checked only once something is typed.
  const infoErrors = {
    phone: form.phone && form.phone.length !== 10 ? "Phone must be 10 digits." : null,
    email: form.email && !EMAIL.test(form.email) ? "Enter a valid email address." : null,
    pincode: form.pincode && form.pincode.length !== 6 ? "PIN must be 6 digits." : null,
  };
  const brandErrors = {
    primary_color: HEX.test(form.primary_color) ? null : "Use a colour like #E85D2E.",
    secondary_color: HEX.test(form.secondary_color) ? null : "Use a colour like #0F766E.",
  };

  const canAdvance = (() => {
    if (stepIndex === 0)
      return (
        form.school_name.length > 1 &&
        form.school_code.length > 1 &&
        /^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(form.subdomain) &&
        !infoErrors.phone && !infoErrors.email && !infoErrors.pincode
      );
    if (stepIndex === 1) return Boolean(form.plan_code);
    if (stepIndex === 2) return !brandErrors.primary_color && !brandErrors.secondary_color;
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
      pincode: form.pincode || undefined,
      phone: form.phone || undefined,
      email: form.email || undefined,
      affiliation_board: form.affiliation_board || undefined,
      medium: form.medium || undefined,
      primary_color: form.primary_color || undefined,
      secondary_color: form.secondary_color || undefined,
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

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
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

        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>{STEPS[stepIndex].title}</CardTitle>
            <CardDescription>{STEPS[stepIndex].description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {stepIndex === 0 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <LogoPicker
                    url={logoUrl}
                    fileName={logoFile?.name ?? null}
                    error={logoError}
                    onPick={pickLogo}
                    onClear={clearLogo}
                  />
                </div>
                <Field label="School name" value={form.school_name} onChange={(v) => set("school_name", v)} required />
                <Field label="School code" value={form.school_code} onChange={(v) => set("school_code", v)} required />
                <Field label="Subdomain" value={form.subdomain} onChange={(v) => set("subdomain", v.toLowerCase())} required hint="lowercase, hyphens ok; will become subdomain.jaikalki.com" />
                <Field
                  label="Phone"
                  value={form.phone}
                  onChange={(v) => set("phone", v.replace(/\D/g, "").slice(0, 10))}
                  inputMode="numeric"
                  maxLength={10}
                  error={infoErrors.phone}
                />
                <Field label="Email" value={form.email} onChange={(v) => set("email", v.trim())} error={infoErrors.email} />
                <LocationFields
                  idPrefix="onboard"
                  state={form.state}
                  city={form.city}
                  onState={(v) => set("state", v)}
                  onCity={(v) => set("city", v)}
                />
                <Field
                  label="PIN"
                  value={form.pincode}
                  onChange={(v) => set("pincode", v.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                  maxLength={6}
                  error={infoErrors.pincode}
                />
              </div>
            )}

            {stepIndex === 1 && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <ColorField
                  id="onboard-primary_color"
                  label="Primary colour"
                  value={form.primary_color}
                  onChange={(v) => set("primary_color", v)}
                  error={brandErrors.primary_color}
                />
                <ColorField
                  id="onboard-secondary_color"
                  label="Secondary colour"
                  value={form.secondary_color}
                  onChange={(v) => set("secondary_color", v)}
                  error={brandErrors.secondary_color}
                />
                <div className="flex flex-wrap items-center gap-3 rounded-lg border border-saffron-pale p-3 sm:col-span-2">
                  <LogoThumb url={logoUrl} size="h-12 w-12" />
                  <span
                    className="rounded-md px-4 py-2 text-sm font-semibold text-white shadow-sm"
                    style={{ background: HEX.test(form.primary_color) ? form.primary_color : undefined }}
                  >
                    {form.school_name || "School"} button
                  </span>
                  <span
                    className="rounded-full px-3 py-1 text-xs font-medium text-white"
                    style={{ background: HEX.test(form.secondary_color) ? form.secondary_color : undefined }}
                  >
                    Badge
                  </span>
                  <p className="text-xs text-muted-foreground">
                    {logoUrl ? "Profile image from School Information." : "No profile image — add one in School Information."}
                  </p>
                </div>
              </div>
            )}

            {stepIndex === 3 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
              <ul className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
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
              <ReviewBlock form={form} planName={selectedPlan?.name ?? form.plan_code} logoUrl={logoUrl} />
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex justify-between border-t border-saffron-pale pt-4">
              <Button
                variant="ghost"
                disabled={stepIndex === 0 || createdId !== null}
                onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                Back
              </Button>
              {createdId !== null ? (
                <Button onClick={() => navigate(`/schools/${createdId}`)}>
                  Open school
                  <ChevronRight className="h-4 w-4" />
                </Button>
              ) : stepIndex < STEPS.length - 1 ? (
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

function LogoThumb({ url, size }: { url: string | null; size: string }) {
  return url ? (
    <img src={url} alt="School profile image" className={cn(size, "shrink-0 rounded-xl border border-saffron-pale bg-white object-contain p-1")} />
  ) : (
    <span className={cn(size, "flex shrink-0 items-center justify-center rounded-xl border border-dashed border-saffron-pale text-muted-foreground")}>
      <School className="h-1/2 w-1/2" />
    </span>
  );
}

function LogoPicker({
  url, fileName, error, onPick, onClear,
}: {
  url: string | null;
  fileName: string | null;
  error: string | null;
  onPick: (f: File) => void;
  onClear: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-saffron-pale p-4">
      <LogoThumb url={url} size="h-20 w-20" />
      <div className="min-w-0 flex-1 space-y-2">
        <div>
          <p className="text-sm font-medium text-indigo-dark">Profile image</p>
          <p className="text-xs text-muted-foreground">
            The school's logo. PNG, JPG or SVG up to {LOGO_MAX_MB} MB; a square image works best.
            Shows in the school's sidebar and on printed ID cards.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={input}
            id="school-logo-file"
            type="file"
            accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = ""; // allow re-picking the same file
              if (f) onPick(f);
            }}
          />
          <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}>
            <ImageUp className="h-4 w-4" />
            {url ? "Change image" : "Upload image"}
          </Button>
          {url && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" /> Remove
            </Button>
          )}
          {fileName && <span className="truncate text-xs text-muted-foreground">{fileName}</span>}
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
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
  error,
  inputMode,
  maxLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  hint?: string;
  error?: string | null;
  inputMode?: "numeric" | "text";
  maxLength?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-destructive"> *</span>}</Label>
      <Input
        value={value}
        inputMode={inputMode}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        className={error ? "border-destructive" : undefined}
      />
      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  );
}

function ReviewBlock({ form, planName, logoUrl }: { form: FormState; planName: string; logoUrl: string | null }) {
  const rows = [
    ["School", form.school_name],
    ["Code", form.school_code],
    ["Subdomain", `${form.subdomain}.jaikalki.com`],
    ["Plan", planName],
    ["Affiliation", form.affiliation_board],
    ["Medium", form.medium],
    ["Location", [form.city, form.state, form.pincode].filter(Boolean).join(", ") || "—"],
    ["Contact", [form.phone, form.email].filter(Boolean).join(" · ") || "—"],
    ["Branding", `${form.primary_color} / ${form.secondary_color}`],
  ] as const;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <LogoThumb url={logoUrl} size="h-14 w-14" />
        <div>
          <p className="font-display text-lg text-indigo-dark">{form.school_name || "—"}</p>
          <p className="text-xs text-muted-foreground">{logoUrl ? "Profile image ready" : "No profile image"}</p>
        </div>
      </div>
      <dl className="grid grid-cols-1 gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-saffron-pale pb-2">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="text-right font-medium text-indigo-dark">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
