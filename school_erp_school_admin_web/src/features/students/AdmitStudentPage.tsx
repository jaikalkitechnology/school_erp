import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listClasses, listSections } from "@/features/setup/api";
import {
  createStudent,
  uploadStudentPhoto,
  type StudentCreatePayload,
} from "./api";
import { StudentAvatar } from "./StudentAvatar";

const CATEGORIES = ["general", "obc", "sc", "st", "ews"] as const;

export function AdmitStudentPage() {
  const navigate = useNavigate();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const [form, setForm] = useState<StudentCreatePayload>({
    full_name: "",
    first_name: "",
    last_name: "",
    date_of_birth: undefined,
    gender: undefined,
    class_def_id: undefined,
    section_id: undefined,
    parent_phone: "",
    parent_email: "",
    father_name: "",
    mother_name: "",
    blood_group: "",
    address: "",
    phone: "",
    category: undefined,
    photo_url: undefined,
  });
  const [error, setError] = useState<string | null>(null);
  const [photoUploading, setPhotoUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const onPhotoPicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoUploading(true);
    setError(null);
    try {
      const path = await uploadStudentPhoto(file);
      set("photo_url", path);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Photo upload failed");
    } finally {
      setPhotoUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const filteredSections = useMemo(
    () => (sections.data ?? []).filter((s) => !form.class_def_id || s.class_def_id === form.class_def_id),
    [sections.data, form.class_def_id],
  );

  const set = <K extends keyof StudentCreatePayload>(k: K, v: StudentCreatePayload[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const submit = useMutation({
    mutationFn: () => createStudent(form),
    onSuccess: (s) => navigate(`/students/${s.id}`),
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not admit student"),
  });

  const canSubmit = form.full_name.length > 1;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 6 · SIS</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Admit a student</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Admission number is auto-generated unless you set one. Siblings are auto-linked when parent
          phone or email matches.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Identity</CardTitle>
          <CardDescription>Required fields are marked with *.</CardDescription>
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
                name={form.full_name || "Student"}
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
            <Field label="Admission number" value={form.admission_number ?? ""} onChange={(v) => set("admission_number", v || undefined)} hint="Leave blank to auto-generate." />
            <Field label="First name" value={form.first_name ?? ""} onChange={(v) => set("first_name", v)} />
            <Field label="Last name" value={form.last_name ?? ""} onChange={(v) => set("last_name", v)} />
            <FieldDate label="Date of birth" value={form.date_of_birth ?? ""} onChange={(v) => set("date_of_birth", v || undefined)} />
            <SelectField
              label="Gender"
              value={form.gender ?? ""}
              onChange={(v) => set("gender", v ? (v as any) : undefined)}
              options={[
                { value: "male", label: "Male" },
                { value: "female", label: "Female" },
                { value: "other", label: "Other" },
              ]}
            />
            <Field label="Blood group" value={form.blood_group ?? ""} onChange={(v) => set("blood_group", v)} />
            <SelectField
              label="Category"
              value={form.category ?? ""}
              onChange={(v) => set("category", v ? (v as any) : undefined)}
              options={CATEGORIES.map((c) => ({ value: c, label: c.toUpperCase() }))}
            />

            <SelectField
              label="Class"
              value={form.class_def_id ?? ""}
              onChange={(v) => { set("class_def_id", v ? Number(v) : undefined); set("section_id", undefined); }}
              options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            />
            <SelectField
              label="Section"
              value={form.section_id ?? ""}
              onChange={(v) => set("section_id", v ? Number(v) : undefined)}
              options={filteredSections.map((s) => ({ value: s.id, label: `Section ${s.name}` }))}
            />

            <Field label="Father's name" value={form.father_name ?? ""} onChange={(v) => set("father_name", v)} />
            <Field label="Mother's name" value={form.mother_name ?? ""} onChange={(v) => set("mother_name", v)} />
            <Field label="Parent phone" value={form.parent_phone ?? ""} onChange={(v) => set("parent_phone", v)} />
            <Field label="Parent email" value={form.parent_email ?? ""} onChange={(v) => set("parent_email", v)} />

            <Field label="Address" value={form.address ?? ""} onChange={(v) => set("address", v)} />
            <Field label="Student phone" value={form.phone ?? ""} onChange={(v) => set("phone", v)} />

            {error && <p className="col-span-2 text-sm text-destructive">{error}</p>}
            <div className="col-span-2 flex justify-end gap-2 border-t border-saffron-pale pt-4">
              <Button type="button" variant="ghost" onClick={() => navigate("/students")}>Cancel</Button>
              <Button type="submit" disabled={!canSubmit || submit.isPending}>
                {submit.isPending ? "Admitting…" : "Admit student"}
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
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
