import { useEffect, useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deleteTenant, updateTenant } from "./api";
import type { SchoolType, Tenant } from "./types";

/** Turn an axios error into one readable sentence. */
function errorText(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) {
    const field = Array.isArray(detail[0].loc) ? detail[0].loc[detail[0].loc.length - 1] : "";
    return `${field ? `${field}: ` : ""}${detail[0].msg}`;
  }
  return fallback;
}

function Modal({
  title, subtitle, onClose, children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-warm-white p-6 shadow-2xl"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 rounded p-1 text-muted-foreground hover:bg-saffron-pale/60 hover:text-indigo-dark"
        >
          <X className="h-5 w-5" />
        </button>
        <h2 className="pr-8 font-display text-2xl text-indigo-dark">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}

// ---- Edit ------------------------------------------------------------------

const SCHOOL_TYPES: { value: SchoolType; label: string }[] = [
  { value: "preschool", label: "Preschool" },
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
  { value: "senior_secondary", label: "Senior secondary" },
  { value: "k12", label: "K-12" },
];

type EditForm = {
  school_name: string;
  affiliation_board: string;
  school_type: SchoolType | "";
  medium: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  timezone: string;
  primary_color: string;
  secondary_color: string;
};

const HEX = /^#[0-9a-fA-F]{6}$/;
const EMAIL = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

function validate(f: EditForm): Record<string, string> {
  const e: Record<string, string> = {};
  if (f.school_name.trim().length < 2) e.school_name = "Enter the school's name.";
  if (f.phone && f.phone.length !== 10) e.phone = "Phone must be 10 digits.";
  if (f.pincode && f.pincode.length !== 6) e.pincode = "PIN must be 6 digits.";
  if (f.email.trim() && !EMAIL.test(f.email.trim())) e.email = "Enter a valid email address.";
  if (!HEX.test(f.primary_color)) e.primary_color = "Use a colour like #E85D2E.";
  if (!HEX.test(f.secondary_color)) e.secondary_color = "Use a colour like #0F766E.";
  return e;
}

export function EditSchoolDialog({ tenant, onClose }: { tenant: Tenant; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<EditForm>({
    school_name: tenant.school_name,
    affiliation_board: tenant.affiliation_board ?? "",
    school_type: tenant.school_type ?? "",
    medium: tenant.medium ?? "",
    address: tenant.address ?? "",
    city: tenant.city ?? "",
    state: tenant.state ?? "",
    pincode: tenant.pincode ?? "",
    phone: tenant.phone ?? "",
    email: tenant.email ?? "",
    timezone: tenant.timezone ?? "Asia/Kolkata",
    primary_color: tenant.primary_color,
    secondary_color: tenant.secondary_color,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = <K extends keyof EditForm>(k: K, v: EditForm[K]) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k])
      setErrors((prev) => {
        const next = { ...prev };
        delete next[k];
        return next;
      });
  };

  const save = useMutation({
    mutationFn: () => {
      // Empty optional boxes are sent as null so they clear the value.
      const opt = (v: string) => (v.trim() ? v.trim() : null);
      return updateTenant(tenant.id, {
        school_name: form.school_name.trim(),
        affiliation_board: opt(form.affiliation_board),
        school_type: form.school_type || null,
        medium: opt(form.medium),
        address: opt(form.address),
        city: opt(form.city),
        state: opt(form.state),
        pincode: opt(form.pincode),
        phone: opt(form.phone),
        email: opt(form.email),
        timezone: form.timezone.trim() || "Asia/Kolkata",
        primary_color: form.primary_color,
        secondary_color: form.secondary_color,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      qc.invalidateQueries({ queryKey: ["tenant", tenant.id] });
      onClose();
    },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate(form);
    setErrors(errs);
    if (Object.keys(errs).length === 0) save.mutate();
  };

  const text = (k: keyof EditForm, label: string, props: Record<string, unknown> = {}) => (
    <div className="space-y-1.5">
      <Label htmlFor={`edit-${k}`}>{label}</Label>
      <Input
        id={`edit-${k}`}
        value={form[k] as string}
        onChange={(e) => set(k, e.target.value as never)}
        className={errors[k] ? "border-destructive" : undefined}
        {...props}
      />
      {errors[k] && <p className="text-xs text-destructive">{errors[k]}</p>}
    </div>
  );

  const color = (k: "primary_color" | "secondary_color", label: string) => (
    <div className="space-y-1.5">
      <Label htmlFor={`edit-${k}`}>{label}</Label>
      <div className="flex gap-2">
        <input
          type="color"
          aria-label={`${label} picker`}
          value={HEX.test(form[k]) ? form[k] : "#000000"}
          onChange={(e) => set(k, e.target.value.toUpperCase())}
          className="h-10 w-12 shrink-0 cursor-pointer rounded-md border border-input bg-transparent p-1"
        />
        <Input
          id={`edit-${k}`}
          value={form[k]}
          maxLength={7}
          onChange={(e) => set(k, e.target.value)}
          className={errors[k] ? "border-destructive font-mono" : "font-mono"}
        />
      </div>
      {errors[k] && <p className="text-xs text-destructive">{errors[k]}</p>}
    </div>
  );

  return (
    <Modal
      title={`Edit ${tenant.school_name}`}
      subtitle={`${tenant.subdomain} · ${tenant.school_code} (subdomain and code can't be changed)`}
      onClose={onClose}
    >
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">{text("school_name", "School name *")}</div>
        {text("affiliation_board", "Affiliation board", { placeholder: "CBSE / ICSE / State" })}
        <div className="space-y-1.5">
          <Label htmlFor="edit-school_type">School type</Label>
          <select
            id="edit-school_type"
            value={form.school_type}
            onChange={(e) => set("school_type", e.target.value as SchoolType | "")}
            className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">Not set</option>
            {SCHOOL_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        {text("medium", "Medium", { placeholder: "English" })}
        {text("timezone", "Timezone", { placeholder: "Asia/Kolkata" })}
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="edit-address">Address</Label>
          <textarea
            id="edit-address"
            rows={2}
            value={form.address}
            onChange={(e) => set("address", e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        {text("city", "City")}
        {text("state", "State")}
        {text("pincode", "PIN", {
          inputMode: "numeric",
          maxLength: 6,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => set("pincode", e.target.value.replace(/\D/g, "").slice(0, 6)),
        })}
        {text("phone", "Phone", {
          inputMode: "numeric",
          maxLength: 10,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => set("phone", e.target.value.replace(/\D/g, "").slice(0, 10)),
        })}
        <div className="sm:col-span-2">{text("email", "Email", { type: "email", placeholder: "office@school.edu" })}</div>
        {color("primary_color", "Primary colour")}
        {color("secondary_color", "Secondary colour")}

        {save.isError && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
            {errorText(save.error, "Could not save the changes. Try again.")}
          </p>
        )}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---- Delete ----------------------------------------------------------------

export function DeleteSchoolDialog({ tenant, onClose }: { tenant: Tenant; onClose: () => void }) {
  const qc = useQueryClient();
  const [typed, setTyped] = useState("");
  const matches = typed.trim().toLowerCase() === tenant.subdomain.toLowerCase();

  const del = useMutation({
    mutationFn: () => deleteTenant(tenant.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      onClose();
    },
  });

  return (
    <Modal title={`Delete ${tenant.school_name}?`} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-indigo-dark">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
          <ul className="list-disc space-y-1 pl-4">
            <li>Everyone at this school is signed out and can no longer log in (web or app).</li>
            <li>Its students, staff, fees and other records are kept, not erased.</li>
            <li>
              A deleted school can't be re-activated, and its subdomain{" "}
              <span className="font-mono text-saffron-darker">{tenant.subdomain}</span> stays taken.
            </li>
          </ul>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm-subdomain">
            Type <span className="font-mono">{tenant.subdomain}</span> to confirm
          </Label>
          <Input
            id="confirm-subdomain"
            autoFocus
            autoComplete="off"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && matches && !del.isPending) del.mutate();
            }}
          />
        </div>
        {del.isError && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {errorText(del.error, "Could not delete the school. Try again.")}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!matches || del.isPending}
            onClick={() => del.mutate()}
            className="bg-destructive text-white hover:bg-destructive/90"
          >
            {del.isPending ? "Deleting…" : "Delete school"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
