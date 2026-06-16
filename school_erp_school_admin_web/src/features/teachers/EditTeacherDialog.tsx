import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listDepartments } from "@/features/setup/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import {
  updateTeacher,
  uploadTeacherPhoto,
  type EmploymentStatus,
  type Teacher,
} from "./api";

interface Props {
  teacher: Teacher;
  open: boolean;
  onClose: () => void;
}

type EditableFields = {
  full_name?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  designation?: string;
  department_id?: number;
  date_of_joining?: string;
  experience_years?: number;
  qualifications?: string[];
  is_class_teacher?: boolean;
  is_available_for_substitution?: boolean;
  employment_status?: EmploymentStatus;
  photo_url?: string;
};

export function EditTeacherDialog({ teacher, open, onClose }: Props) {
  const qc = useQueryClient();
  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });

  const [form, setForm] = useState<EditableFields>({});
  const [qualText, setQualText] = useState("");
  const [photoUrl, setPhotoUrl] = useState<string | null>(teacher.photo_url);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Reset form whenever a different teacher loads.
  useEffect(() => {
    if (!open) return;
    setForm({
      full_name: teacher.full_name,
      first_name: teacher.first_name ?? "",
      last_name: teacher.last_name ?? "",
      email: teacher.email ?? "",
      phone: teacher.phone ?? "",
      designation: teacher.designation ?? "",
      department_id: teacher.department_id ?? undefined,
      date_of_joining: teacher.date_of_joining ?? undefined,
      experience_years: teacher.experience_years ?? 0,
      is_class_teacher: teacher.is_class_teacher,
      is_available_for_substitution: teacher.is_available_for_substitution,
      employment_status: teacher.employment_status,
    });
    setQualText((teacher.qualifications ?? []).join(", "));
    setPhotoUrl(teacher.photo_url);
    setError(null);
  }, [teacher.id, open]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () =>
      updateTeacher(teacher.id, {
        ...form,
        qualifications: qualText
          .split(",")
          .map((q) => q.trim())
          .filter(Boolean),
        photo_url: photoUrl ?? undefined,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["teachers"] });
      qc.invalidateQueries({ queryKey: ["teacher", teacher.id] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Could not save"),
  });

  const onPhotoPicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoUploading(true);
    setError(null);
    try {
      const path = await uploadTeacherPhoto(file);
      setPhotoUrl(path);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Photo upload failed");
    } finally {
      setPhotoUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-background p-6 shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="font-display text-2xl text-indigo-dark">Edit teacher</h2>
        <p className="text-xs text-muted-foreground">{teacher.employee_no}</p>

        <div className="mt-4 flex items-center gap-4">
          <StudentAvatar
            photoUrl={photoUrl}
            name={form.full_name ?? teacher.full_name}
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
              {photoUploading ? "Uploading…" : photoUrl ? "Replace photo" : "Add photo"}
            </Button>
            {photoUrl && (
              <button
                type="button"
                onClick={() => setPhotoUrl(null)}
                className="text-left text-[11px] text-destructive hover:underline"
              >
                Remove photo
              </button>
            )}
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
          <Field
            label="Full name"
            value={form.full_name ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, full_name: v }))}
          />
          <Field
            label="Designation"
            value={form.designation ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, designation: v }))}
          />
          <Field
            label="First name"
            value={form.first_name ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, first_name: v }))}
          />
          <Field
            label="Last name"
            value={form.last_name ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, last_name: v }))}
          />
          <Field
            label="Email"
            value={form.email ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, email: v }))}
            type="email"
          />
          <Field
            label="Phone"
            value={form.phone ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, phone: v }))}
          />
          <Field
            label="Date of joining"
            type="date"
            value={form.date_of_joining ?? ""}
            onChange={(v) =>
              setForm((f) => ({ ...f, date_of_joining: v || undefined }))
            }
          />
          <div className="space-y-1.5">
            <Label>Experience (years)</Label>
            <Input
              type="number"
              value={form.experience_years ?? 0}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  experience_years: Math.max(0, Number(e.target.value) || 0),
                }))
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>Department</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={form.department_id ?? ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  department_id: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            >
              <option value="">—</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Employment status</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={form.employment_status ?? "active"}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  employment_status: e.target.value as EmploymentStatus,
                }))
              }
            >
              <option value="active">Active</option>
              <option value="on_leave">On leave</option>
              <option value="resigned">Resigned</option>
            </select>
          </div>
          <div className="md:col-span-2 space-y-1.5">
            <Label>Qualifications (comma separated)</Label>
            <Input
              value={qualText}
              onChange={(e) => setQualText(e.target.value)}
              placeholder='B.Ed, M.Sc Math'
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_class_teacher ?? false}
              onChange={(e) =>
                setForm((f) => ({ ...f, is_class_teacher: e.target.checked }))
              }
            />
            Class teacher
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_available_for_substitution ?? true}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  is_available_for_substitution: e.target.checked,
                }))
              }
            />
            Available for substitutions
          </label>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => save.mutate()}
            disabled={save.isPending || photoUploading}
          >
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text",
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
