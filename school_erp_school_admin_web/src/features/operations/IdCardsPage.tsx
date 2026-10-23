import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Printer, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SchoolLogo } from "@/components/SchoolLogo";
import { fetchBranding } from "@/lib/branding-api";
import { cn } from "@/lib/utils";
import { listStudents, updateStudent, uploadStudentPhoto, type Student } from "@/features/students/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import { fetchSettings, type SchoolSettings } from "@/features/setup/api";

type Side = "front" | "back";

/** Bulk ID-card generator. Reads students from the SIS, filters
 * by class + search, renders printable card previews. Click a card to
 * flip it; the Front / Back switch flips them all, and Print prints the
 * side showing. Print dialog handles paper; CSS hides the sidebar. */
export function IdCardsPage() {
  const [q, setQ] = useState("");
  const [classFilter, setClassFilter] = useState("");
  // null = use the school's own name from School Profile.
  const [orgLine, setOrgLine] = useState<string | null>(null);
  const [side, setSide] = useState<Side>("front");
  // Cards flipped by clicking, i.e. showing the other side to `side`.
  const [flipped, setFlipped] = useState<Set<number>>(new Set());

  const branding = useQuery({ queryKey: ["branding"], queryFn: fetchBranding, staleTime: 5 * 60_000 });
  // School address for the back; roles without settings access just skip it.
  const settings = useQuery({ queryKey: ["settings"], queryFn: fetchSettings, retry: false, staleTime: 5 * 60_000 });
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

  const showAll = (s: Side) => {
    setSide(s);
    setFlipped(new Set());
  };
  const flip = (id: number) =>
    setFlipped((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  return (
    <div className="space-y-6 print:space-y-2">
      <header className="print:hidden">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">ID cards</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Bulk-generate ID cards from your student roster. Click a card to see
          its back. Print the front, then switch to Back and print again on the
          other side of the sheet.
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
          <div className="col-span-full flex flex-wrap items-center gap-3">
            <div role="radiogroup" aria-label="Card side" className="inline-flex rounded-md border border-input p-0.5">
              {(["front", "back"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  role="radio"
                  aria-checked={side === s && flipped.size === 0}
                  onClick={() => showAll(s)}
                  className={cn(
                    "rounded px-3 py-1.5 text-sm",
                    side === s && flipped.size === 0 ? "bg-indigo-dark text-white" : "text-indigo-dark hover:bg-muted",
                  )}
                >
                  {s === "front" ? "Front side" : "Back side"}
                </button>
              ))}
            </div>
            <Button onClick={() => window.print()}>
              <Printer className="mr-1 h-4 w-4" /> Print {flipped.size === 0 ? `${side} side` : "as shown"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Backs print right-to-left so each lines up behind its front
          when the sheet is turned over on its long edge. */}
      <div
        className={cn(
          "grid grid-cols-2 gap-3 md:grid-cols-3 print:grid-cols-3 print:gap-2",
          side === "back" && flipped.size === 0 && "print:[direction:rtl]",
        )}
      >
        {filtered.map((s) => (
          <IdCard
            key={s.id}
            student={s}
            header={header}
            logoUrl={branding.data?.logo_url}
            school={settings.data}
            showBack={(side === "back") !== flipped.has(s.id)}
            onFlip={() => flip(s.id)}
          />
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

const faceBase = cn(
  "flex flex-col overflow-hidden rounded-lg border-2 border-saffron bg-white shadow-sm [grid-area:1/1] [backface-visibility:hidden]",
  "print:shadow-none print:[transform:none] print:[print-color-adjust:exact]",
);

/** One card. Both faces share a grid cell so the card is as tall as the
 *  taller face (front and back print the same size), and turn over with a
 *  3D flip. Printing drops the 3D and hides the face that isn't showing. */
function IdCard({
  student: s, header, logoUrl, school, showBack, onFlip,
}: {
  student: Student;
  header: string;
  logoUrl: string | null | undefined;
  school: SchoolSettings | undefined;
  showBack: boolean;
  onFlip: () => void;
}) {
  return (
    <div className="[perspective:1200px] [direction:ltr] print:break-inside-avoid">
      <div
        role="button"
        tabIndex={0}
        aria-label={`${s.full_name} ID card, ${showBack ? "back" : "front"}. Click to flip.`}
        onClick={onFlip}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onFlip();
          }
        }}
        className={cn(
          "group relative grid h-full cursor-pointer transition-transform duration-500 [transform-style:preserve-3d] focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron print:[transform:none]",
          showBack && "[transform:rotateY(180deg)]",
        )}
      >
        <div className={cn(faceBase, showBack && "print:invisible")}>
          <CardBand header={header} logoUrl={logoUrl} title="STUDENT ID CARD" />
          <div className="flex flex-1 gap-3 p-3">
            <CardPhoto student={s} />
            <div className="flex-1 text-xs">
              <p className="text-sm font-semibold text-indigo-dark">{s.full_name}</p>
              <p className="mt-0.5 text-muted-foreground">
                Admn: <span className="font-mono">{s.admission_number}</span>
              </p>
              <p className="text-muted-foreground">Class: {s.current_class_label ?? "—"}</p>
              {s.roll_no && <p className="text-muted-foreground">Roll: {s.roll_no}</p>}
              {s.blood_group && <p className="text-muted-foreground">Blood: {s.blood_group}</p>}
            </div>
          </div>
          <div className="flex items-center justify-center gap-1 border-t border-input bg-muted/40 px-3 py-1 text-center text-[10px] text-muted-foreground">
            Valid for the academic session · If found, please return.
            <RotateCw className="h-3 w-3 shrink-0 opacity-60 group-hover:opacity-100 print:hidden" aria-hidden />
          </div>
        </div>

        <div className={cn(faceBase, "[transform:rotateY(180deg)]", !showBack && "print:invisible")}>
          <CardBand header={header} logoUrl={logoUrl} title="STUDENT DETAILS" />
          <dl className="grid flex-1 grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 px-3 py-2 text-[11px] leading-snug">
            <BackRow label="Father" value={s.father_name} />
            <BackRow label="Mother" value={s.mother_name} />
            {!s.father_name && !s.mother_name && <BackRow label="Guardian" value={s.guardian_name} />}
            <BackRow label="Date of birth" value={formatDob(s.date_of_birth)} />
            <BackRow label="Parent phone" value={s.parent_phone} />
            <BackRow label="Emergency" value={emergency(s)} />
            <BackRow label="Address" value={s.address} />
          </dl>
          <div className="flex items-end justify-between gap-2 px-3 pb-1.5">
            <p className="text-[9px] text-muted-foreground">
              Admn <span className="font-mono">{s.admission_number}</span>
            </p>
            <p className="w-24 border-t border-indigo-dark/40 pt-0.5 text-center text-[9px] text-muted-foreground">
              Principal
            </p>
          </div>
          <div className="flex items-center justify-center gap-1 border-t border-input bg-muted/40 px-3 py-1 text-center text-[10px] leading-tight text-muted-foreground">
            <span>
              If found, please return to <b className="font-semibold text-indigo-dark">{header}</b>
              {schoolAddress(school) && <>, {schoolAddress(school)}</>}
              {school?.phone && <> · Ph {school.phone}</>}
            </span>
            <RotateCw className="h-3 w-3 shrink-0 opacity-60 group-hover:opacity-100 print:hidden" aria-hidden />
          </div>
        </div>
      </div>
    </div>
  );
}

function CardBand({ header, logoUrl, title }: { header: string; logoUrl: string | null | undefined; title: string }) {
  return (
    <div className="flex items-center justify-center gap-2 bg-saffron px-3 py-2 text-warm-white">
      <SchoolLogo src={logoUrl} alt="" className="h-7 w-7 shrink-0 rounded bg-white object-contain p-0.5" />
      <div className="text-center">
        <p className="text-[10px] uppercase tracking-[0.2em]">{header}</p>
        <p className="text-xs font-bold">{title}</p>
      </div>
    </div>
  );
}

function BackRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-indigo-dark">{value?.trim() || "—"}</dd>
    </>
  );
}

function formatDob(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function emergency(s: Student): string | null {
  const parts = [s.emergency_contact_name, s.emergency_phone].filter((p) => p?.trim());
  return parts.length ? parts.join(" · ") : null;
}

function schoolAddress(school: SchoolSettings | undefined): string {
  if (!school) return "";
  const cityLine = [school.city, school.state].filter(Boolean).join(", ");
  return [school.address, [cityLine, school.pincode].filter(Boolean).join(" - ")].filter(Boolean).join(", ");
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
    // Clicks here add a photo instead of flipping the card.
    <div className="relative h-24 w-24 shrink-0" onClick={(e) => e.stopPropagation()}>
      <StudentAvatar
        photoUrl={student.photo_url}
        name={student.full_name}
        size={96}
        className="rounded border border-input bg-muted text-3xl font-normal text-muted-foreground"
      />
      <button
        type="button"
        onClick={() => input.current?.click()}
        onKeyDown={(e) => e.stopPropagation()}
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
