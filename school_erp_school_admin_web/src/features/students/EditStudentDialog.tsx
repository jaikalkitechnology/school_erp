import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listClasses, listSections } from "@/features/setup/api";
import {
  updateStudent,
  uploadStudentPhoto,
  type Student,
  type StudentCreatePayload,
  type StudentStatus,
} from "./api";
import { StudentAvatar } from "./StudentAvatar";

interface Props {
  student: Student;
  open: boolean;
  onClose: () => void;
}

type EditableFields = Partial<StudentCreatePayload> & {
  status?: StudentStatus;
  roll_no?: string;
  photo_url?: string;
};

export function EditStudentDialog({ student, open, onClose }: Props) {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const [form, setForm] = useState<EditableFields>({});
  const [photoUrl, setPhotoUrl] = useState<string | null>(student.photo_url);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Reset form whenever a different student loads into the dialog.
  useEffect(() => {
    if (!open) return;
    setForm({
      full_name: student.full_name,
      first_name: student.first_name ?? "",
      last_name: student.last_name ?? "",
      date_of_birth: student.date_of_birth ?? "",
      gender: (student.gender as any) ?? undefined,
      blood_group: student.blood_group ?? "",
      class_def_id: student.class_def_id ?? undefined,
      section_id: student.section_id ?? undefined,
      address: student.address ?? "",
      phone: student.phone ?? "",
      father_name: student.father_name ?? "",
      mother_name: student.mother_name ?? "",
      parent_phone: student.parent_phone ?? "",
      parent_email: student.parent_email ?? "",
      roll_no: student.roll_no ?? "",
      status: student.status,
    });
    setPhotoUrl(student.photo_url);
    setError(null);
  }, [student.id, open]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () =>
      updateStudent(student.id, {
        ...form,
        // Always send the current photo_url so clearing the photo (set
        // to null externally) actually persists.
        photo_url: photoUrl ?? undefined,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["student", student.id] });
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
      const path = await uploadStudentPhoto(file);
      setPhotoUrl(path);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Photo upload failed");
    } finally {
      setPhotoUploading(false);
      // Clear so picking the same file again still fires onChange.
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

        <h2 className="font-display text-2xl text-indigo-dark">Edit student</h2>
        <p className="text-xs text-muted-foreground">
          {student.admission_number}
        </p>

        {/* Photo block */}
        <div className="mt-4 flex items-center gap-4">
          <StudentAvatar
            photoUrl={photoUrl}
            name={form.full_name ?? student.full_name}
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
            label="Roll no."
            value={form.roll_no ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, roll_no: v }))}
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
            label="Date of birth"
            type="date"
            value={form.date_of_birth ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, date_of_birth: v }))}
          />
          <div className="space-y-1.5">
            <Label>Gender</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={form.gender ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, gender: (e.target.value || undefined) as any }))
              }
            >
              <option value="">—</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <Field
            label="Blood group"
            value={form.blood_group ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, blood_group: v }))}
          />
          <div className="space-y-1.5">
            <Label>Class</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={form.class_def_id ?? ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  class_def_id: e.target.value ? Number(e.target.value) : undefined,
                  section_id: undefined,
                }))
              }
            >
              <option value="">—</option>
              {(classes.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Section</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={form.section_id ?? ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  section_id: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            >
              <option value="">—</option>
              {(sections.data ?? [])
                .filter((s) => !form.class_def_id || s.class_def_id === form.class_def_id)
                .map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
            </select>
          </div>
          <Field
            label="Phone"
            kind="phone"
            value={form.phone ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, phone: v }))}
          />
          <Field
            label="Father's name"
            value={form.father_name ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, father_name: v }))}
          />
          <Field
            label="Mother's name"
            value={form.mother_name ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, mother_name: v }))}
          />
          <Field
            label="Parent phone"
            kind="phone"
            value={form.parent_phone ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, parent_phone: v }))}
          />
          <Field
            label="Parent email"
            kind="email"
            value={form.parent_email ?? ""}
            onChange={(v) => setForm((f) => ({ ...f, parent_email: v }))}
          />
          <div className="md:col-span-2 space-y-1.5">
            <Label>Address</Label>
            <textarea
              className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.address ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
            />
          </div>
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
  label,
  value,
  onChange,
  type = "text",
  kind,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  kind?: "phone" | "email";
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        type={kind === "email" ? "email" : kind === "phone" ? "tel" : type}
        inputMode={kind === "phone" ? "numeric" : undefined}
        maxLength={kind === "phone" ? 10 : undefined}
        value={value}
        onChange={(e) => {
          const v =
            kind === "phone"
              ? e.target.value.replace(/\D/g, "").slice(0, 10)
              : e.target.value;
          onChange(v);
        }}
      />
    </div>
  );
}
