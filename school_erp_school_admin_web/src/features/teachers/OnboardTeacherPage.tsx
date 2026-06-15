import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listDepartments } from "@/features/setup/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import {
  createTeacher,
  uploadTeacherPhoto,
  type TeacherCreatePayload,
} from "./api";

const ROLE_CHOICES = [
  { code: "subject_teacher", label: "Subject Teacher" },
  { code: "class_teacher", label: "Class Teacher" },
  { code: "coordinator", label: "Coordinator (HOD)" },
  { code: "vice_principal", label: "Vice Principal" },
  { code: "principal", label: "Principal" },
] as const;

export function OnboardTeacherPage() {
  const navigate = useNavigate();
  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });

  const [form, setForm] = useState<TeacherCreatePayload>({
    full_name: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    password: "",
    qualifications: [],
    experience_years: 0,
    department_id: undefined,
    designation: "",
    date_of_joining: undefined,
    is_class_teacher: false,
    is_available_for_substitution: true,
    role_codes: ["subject_teacher"],
  });
  const [qualText, setQualText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [photoUploading, setPhotoUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const set = <K extends keyof TeacherCreatePayload>(k: K, v: TeacherCreatePayload[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const onPhotoPicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoUploading(true);
    setError(null);
    try {
      const path = await uploadTeacherPhoto(file);
      set("photo_url", path);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Photo upload failed");
    } finally {
      setPhotoUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const toggleRole = (code: string) => {
    setForm((s) => {
      const current = new Set(s.role_codes ?? []);
      if (current.has(code)) current.delete(code);
      else current.add(code);
      return { ...s, role_codes: Array.from(current.size ? current : new Set(["subject_teacher"])) };
    });
  };

  const submit = useMutation({
    mutationFn: () => createTeacher({
      ...form,
      qualifications: qualText
        .split(",")
        .map((q) => q.trim())
        .filter(Boolean),
    }),
    onSuccess: (t) => navigate(`/teachers/${t.id}`),
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not onboard teacher"),
  });

  const canSubmit =
    form.full_name.length > 1 &&
    form.password.length >= 6 &&
    (form.email || form.phone) &&
    (form.role_codes?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 7 · Staff</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Onboard a teacher</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Creates a User with the chosen role(s); employee number is auto-generated when blank.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
          <CardDescription>Email or phone is required for sign-in.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-2 gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              submit.mutate();
            }}
          >
            <div className="col-span-2 flex items-center gap-4 border-b border-saffron-pale pb-4">
              <StudentAvatar
                photoUrl={form.photo_url ?? null}
                name={form.full_name || "Teacher"}
                size={72}
              />
              <div className="flex flex-col gap-1">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png"
                  className="hidden"
                  onChange={onPhotoPicked}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={photoUploading}
                  onClick={() => fileRef.current?.click()}
                >
                  <Camera className="h-4 w-4" />
                  {photoUploading
                    ? "Uploading…"
                    : form.photo_url
                      ? "Replace photo"
                      : "Add photo"}
                </Button>
                {form.photo_url && (
                  <button
                    type="button"
                    onClick={() => set("photo_url", undefined)}
                    className="text-left text-[11px] text-destructive hover:underline"
                  >
                    Remove photo
                  </button>
                )}
                <p className="text-[11px] text-muted-foreground">JPG or PNG.</p>
              </div>
            </div>
            <Field label="Full name *" value={form.full_name} onChange={(v) => set("full_name", v)} />
            <Field label="Employee number" value={form.employee_no ?? ""} onChange={(v) => set("employee_no", v || undefined)} hint="Leave blank to auto-generate." />
            <Field label="First name" value={form.first_name ?? ""} onChange={(v) => set("first_name", v)} />
            <Field label="Last name" value={form.last_name ?? ""} onChange={(v) => set("last_name", v)} />
            <Field label="Email" value={form.email ?? ""} onChange={(v) => set("email", v)} />
            <Field label="Phone" value={form.phone ?? ""} onChange={(v) => set("phone", v)} />
            <Field label="Password *" value={form.password} onChange={(v) => set("password", v)} hint="Min 6 chars; teacher can change on first login." />
            <Field label="Designation" value={form.designation ?? ""} onChange={(v) => set("designation", v)} />
            <FieldNum label="Experience (years)" value={form.experience_years ?? 0} onChange={(v) => set("experience_years", v)} />
            <FieldDate label="Date of joining" value={form.date_of_joining ?? ""} onChange={(v) => set("date_of_joining", v || undefined)} />
            <SelectField
              label="Department"
              value={form.department_id ?? ""}
              onChange={(v) => set("department_id", v ? Number(v) : undefined)}
              options={(departments.data ?? []).map((d) => ({ value: d.id, label: d.name }))}
            />
            <Field
              label="Qualifications (comma separated)"
              value={qualText}
              onChange={setQualText}
              hint='e.g. "B.Ed, M.Sc Math"'
            />

            <div className="col-span-2 space-y-1.5">
              <Label>Roles *</Label>
              <div className="flex flex-wrap gap-2">
                {ROLE_CHOICES.map((r) => {
                  const selected = (form.role_codes ?? []).includes(r.code);
                  return (
                    <button
                      key={r.code}
                      type="button"
                      onClick={() => toggleRole(r.code)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                        selected
                          ? "border-saffron bg-saffron-pale text-saffron-darker"
                          : "border-border text-muted-foreground hover:border-saffron-light"
                      }`}
                    >
                      {r.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="col-span-2 flex items-center gap-6">
              <CheckboxRow
                label="Available for substitutions"
                checked={form.is_available_for_substitution ?? true}
                onChange={(v) => set("is_available_for_substitution", v)}
              />
              <CheckboxRow
                label="Class teacher"
                checked={form.is_class_teacher ?? false}
                onChange={(v) => set("is_class_teacher", v)}
              />
            </div>

            {error && <p className="col-span-2 text-sm text-destructive">{error}</p>}
            <div className="col-span-2 flex justify-end gap-2 border-t border-saffron-pale pt-4">
              <Button type="button" variant="ghost" onClick={() => navigate("/teachers")}>Cancel</Button>
              <Button type="submit" disabled={!canSubmit || submit.isPending}>
                {submit.isPending ? "Onboarding…" : "Onboard teacher"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function FieldNum({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="number" value={value} onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))} />
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

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  options: { value: string | number; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— pick one —</option>
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function CheckboxRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-saffron"
      />
      {label}
    </label>
  );
}
