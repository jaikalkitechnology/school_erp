import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SchoolLogo } from "@/components/SchoolLogo";
import { fetchBranding } from "@/lib/branding-api";
import { cn } from "@/lib/utils";
import { listStudents, updateStudent, uploadStudentPhoto, type Student } from "@/features/students/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";

/** Bulk ID-card generator. Reads students from the SIS, filters
 * by class + search, renders printable card previews. Print
 * dialog handles paper; CSS hides the sidebar during printing. */
export function IdCardsPage() {
  const [q, setQ] = useState("");
  const [classFilter, setClassFilter] = useState("");
  // null = use the school's own name from School Profile.
  const [orgLine, setOrgLine] = useState<string | null>(null);

  const branding = useQuery({ queryKey: ["branding"], queryFn: fetchBranding, staleTime: 5 * 60_000 });
  const header = orgLine ?? branding.data?.school_name ?? "";

  const { data } = useQuery({
    queryKey: ["id-cards-students", q, classFilter],
    queryFn: () => listStudents({ q: q || undefined, limit: 200 }),
  });
  const students = data?.items ?? [];
  const filtered = useMemo(
    () =>
      classFilter
        ? students.filter((s) => (s.current_class_label ?? "").includes(classFilter))
        : students,
    [students, classFilter],
  );
  const missingPhotos = filtered.filter((s) => !s.photo_url).length;

  return (
    <div className="space-y-6 print:space-y-2">
      <header className="print:hidden">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">ID cards</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Bulk-generate ID cards from your student roster. Filter by class,
          click Print — set page size to your card sheet in the browser dialog.
        </p>
      </header>

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Filter + branding</CardTitle>
          <CardDescription>
            {filtered.length} cards will be rendered below
            {missingPhotos > 0 && (
              <> · {missingPhotos} without a photo — click the camera on a card to add one</>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label>Search</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or admission" />
          </div>
          <div>
            <Label>Class filter</Label>
            <Input value={classFilter} onChange={(e) => setClassFilter(e.target.value)} placeholder="e.g. 8-A" />
          </div>
          <div className="col-span-2">
            <Label>School header (on every card)</Label>
            <Input value={header} onChange={(e) => setOrgLine(e.target.value)} />
          </div>
          <div>
            <Button onClick={() => window.print()}>
              <Printer className="mr-1 h-4 w-4" /> Print all
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 print:grid-cols-3 print:gap-2">
        {filtered.map((s) => (
          <div
            key={s.id}
            className={cn(
              "flex flex-col overflow-hidden rounded-lg border-2 border-saffron bg-white shadow-sm",
              "print:break-inside-avoid print:shadow-none",
            )}
          >
            <div className="flex items-center justify-center gap-2 bg-saffron px-3 py-2 text-warm-white">
              <SchoolLogo
                src={branding.data?.logo_url}
                alt=""
                className="h-7 w-7 shrink-0 rounded bg-white object-contain p-0.5"
              />
              <div className="text-center">
                <p className="text-[10px] uppercase tracking-[0.2em]">{header}</p>
                <p className="text-xs font-bold">STUDENT ID CARD</p>
              </div>
            </div>
            <div className="flex flex-1 gap-3 p-3">
              <CardPhoto student={s} />
              <div className="flex-1 text-xs">
                <p className="text-sm font-semibold text-indigo-dark">
                  {s.full_name}
                </p>
                <p className="mt-0.5 text-muted-foreground">
                  Admn: <span className="font-mono">{s.admission_number}</span>
                </p>
                <p className="text-muted-foreground">
                  Class: {s.current_class_label ?? "—"}
                </p>
                {s.roll_no && (
                  <p className="text-muted-foreground">Roll: {s.roll_no}</p>
                )}
                {s.blood_group && (
                  <p className="text-muted-foreground">Blood: {s.blood_group}</p>
                )}
              </div>
            </div>
            <div className="border-t border-input bg-muted/40 px-3 py-1 text-center text-[10px] text-muted-foreground">
              Valid for the academic session · If found, please return.
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="col-span-full text-sm text-muted-foreground">
            No students match. Adjust the filters above.
          </p>
        )}
      </div>
    </div>
  );
}

/** The student's profile photo (initials if none), with a camera button
 *  to add or replace it. The button isn't printed. */
function CardPhoto({ student }: { student: Student }) {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: async (file: File) =>
      updateStudent(student.id, { photo_url: await uploadStudentPhoto(file) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["id-cards-students"] });
      qc.invalidateQueries({ queryKey: ["students"] });
    },
  });
  return (
    <div className="relative h-24 w-24 shrink-0">
      <StudentAvatar
        photoUrl={student.photo_url}
        name={student.full_name}
        size={96}
        className="rounded border border-input bg-muted text-3xl font-normal text-muted-foreground"
      />
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={upload.isPending}
        title={student.photo_url ? "Change photo" : "Add photo"}
        aria-label={`${student.photo_url ? "Change" : "Add"} photo for ${student.full_name}`}
        className="absolute bottom-1 right-1 rounded-full bg-indigo-dark/80 p-1.5 text-white shadow hover:bg-indigo-dark disabled:opacity-60 print:hidden"
      >
        <Camera className="h-3.5 w-3.5" />
      </button>
      {upload.isPending && (
        <span className="absolute inset-x-0 top-1 text-center text-[10px] text-indigo-dark print:hidden">Uploading…</span>
      )}
      {upload.isError && (
        <span className="absolute inset-x-0 top-1 text-center text-[10px] text-destructive print:hidden">Upload failed</span>
      )}
      <input
        ref={input}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload.mutate(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
