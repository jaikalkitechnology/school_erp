import { useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BookOpenCheck, Briefcase, Camera, ClipboardList, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listSections, listSubjects } from "@/features/setup/api";
import { listSectionSubjects } from "@/features/curriculum/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import {
  assignClassTeacher,
  assignSectionSubject,
  clearSectionSubjectTeacher,
  getTeacher,
  getWorkload,
  listAttendance,
  listQualifiedSubjects,
  setQualifiedSubjects,
  updateTeacher,
  uploadTeacherPhoto,
  upsertAttendance,
  type AttendanceStatus,
} from "./api";

const TABS = ["Profile", "Subjects", "Classes", "Workload", "Attendance"] as const;
type Tab = (typeof TABS)[number];

export function TeacherDetailPage() {
  const { id } = useParams<{ id: string }>();
  const tid = Number(id);
  const navigate = useNavigate();

  const qc = useQueryClient();
  const teacher = useQuery({
    queryKey: ["teacher", tid],
    queryFn: () => getTeacher(tid),
    enabled: !Number.isNaN(tid),
  });

  const [tab, setTab] = useState<Tab>("Profile");
  const [photoUploading, setPhotoUploading] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const photoMut = useMutation({
    mutationFn: (photo_url: string | null) =>
      updateTeacher(tid, { photo_url: photo_url ?? "" } as any),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher", tid] }),
  });

  const onPhotoPicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoUploading(true);
    setPhotoError(null);
    try {
      const path = await uploadTeacherPhoto(file);
      await photoMut.mutateAsync(path);
    } catch (err: any) {
      setPhotoError(err?.response?.data?.detail ?? "Photo upload failed");
    } finally {
      setPhotoUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  if (teacher.isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (teacher.isError || !teacher.data) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-destructive">Could not load this teacher.</p>
        </CardContent>
      </Card>
    );
  }
  const t = teacher.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <Button variant="ghost" size="sm" onClick={() => navigate("/teachers")}>
          <ArrowLeft className="h-4 w-4" />
          All teachers
        </Button>
      </div>

      <header className="flex items-start gap-5">
        <div className="flex flex-col items-center gap-1">
          <StudentAvatar photoUrl={t.photo_url} name={t.full_name} size={96} />
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
            disabled={photoUploading || photoMut.isPending}
            onClick={() => fileRef.current?.click()}
          >
            <Camera className="h-3 w-3" />
            {photoUploading
              ? "Uploading…"
              : t.photo_url
                ? "Replace"
                : "Add photo"}
          </Button>
          {t.photo_url && (
            <button
              type="button"
              onClick={() => photoMut.mutate(null)}
              className="text-[10px] text-destructive hover:underline"
            >
              Remove
            </button>
          )}
          {photoError && (
            <p className="max-w-[120px] text-[10px] text-destructive">{photoError}</p>
          )}
        </div>
        <div className="flex-1">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">{t.employee_no}</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">{t.full_name}</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            {t.designation ?? "—"} · {(t.qualifications || []).join(", ") || "no qualifications listed"} ·{" "}
            <span className="font-medium uppercase">{t.employment_status.replace(/_/g, " ")}</span>
          </p>
        </div>
      </header>

      <nav className="flex gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label ? "border-b-2 border-saffron text-saffron-darker" : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "Profile" && <ProfileTab t={t} />}
      {tab === "Subjects" && <SubjectsTab teacherId={t.id} />}
      {tab === "Classes" && <ClassesTab teacherId={t.id} />}
      {tab === "Workload" && <WorkloadTab teacherId={t.id} />}
      {tab === "Attendance" && <AttendanceTab teacherId={t.id} />}
    </div>
  );
}

function Pair({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-2 border-b border-saffron-pale py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-indigo-dark">{value || "—"}</dd>
    </div>
  );
}

function ProfileTab({ t }: { t: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Pair label="First name" value={t.first_name} />
            <Pair label="Last name" value={t.last_name} />
            <Pair label="Date of birth" value={t.date_of_birth} />
            <Pair label="Gender" value={t.gender} />
            <Pair label="Blood group" value={t.blood_group} />
          </div>
          <div>
            <Pair label="Phone" value={t.phone} />
            <Pair label="Email" value={t.email} />
            <Pair label="Address" value={t.address} />
            <Pair label="Date of joining" value={t.date_of_joining} />
            <Pair label="Experience" value={`${t.experience_years} years`} />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function SubjectsTab({ teacherId }: { teacherId: number }) {
  const qc = useQueryClient();
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });
  const qualified = useQuery({
    queryKey: ["teacher-subjects", teacherId],
    queryFn: () => listQualifiedSubjects(teacherId),
  });

  const replace = useMutation({
    mutationFn: (subject_ids: number[]) => setQualifiedSubjects(teacherId, subject_ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher-subjects", teacherId] }),
  });

  const linkedIds = new Set((qualified.data ?? []).map((q) => q.subject_id));

  const toggle = (subjectId: number) => {
    const next = new Set(linkedIds);
    if (next.has(subjectId)) next.delete(subjectId);
    else next.add(subjectId);
    replace.mutate(Array.from(next));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Qualified subjects</CardTitle>
        <CardDescription>
          Tap to toggle. Subjects this teacher is qualified for; assignment to specific sections happens
          on the Classes tab.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!subjects.data?.length ? (
          <p className="text-sm text-muted-foreground">Add subjects on the Org page first.</p>
        ) : (
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {subjects.data.map((s) => {
              const linked = linkedIds.has(s.id);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => toggle(s.id)}
                  className={cn(
                    "rounded-md border p-3 text-left transition-colors",
                    linked
                      ? "border-saffron bg-saffron-pale text-saffron-darker"
                      : "border-border hover:border-saffron-light",
                  )}
                >
                  <p className="font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.code}</p>
                </button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ClassesTab({ teacherId }: { teacherId: number }) {
  const qc = useQueryClient();
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });
  const [sectionId, setSectionId] = useState<number | "">("");
  const sectionSubjects = useQuery({
    queryKey: ["section-subjects", sectionId || null],
    queryFn: () => listSectionSubjects(sectionId === "" ? undefined : Number(sectionId)),
    enabled: sectionId !== "",
  });

  const assignSS = useMutation({
    mutationFn: (ss_id: number) => assignSectionSubject(teacherId, ss_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["section-subjects"] }),
  });
  const clearSS = useMutation({
    mutationFn: (ss_id: number) => clearSectionSubjectTeacher(ss_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["section-subjects"] }),
  });
  const setClassTeacher = useMutation({
    mutationFn: (section_id: number) => assignClassTeacher(teacherId, section_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sections"] }),
  });

  const subjectMap = useMemo(
    () => new Map((subjects.data ?? []).map((s) => [s.id, s])),
    [subjects.data],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick a section</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-[2fr_auto] lg:items-center">
          <select
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">— pick a section —</option>
            {(sections.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>Section #{s.id} (class {s.class_def_id})</option>
            ))}
          </select>
          <Button
            disabled={sectionId === "" || setClassTeacher.isPending}
            onClick={() => setClassTeacher.mutate(Number(sectionId))}
          >
            <Sparkles className="h-4 w-4" />
            Make class teacher of this section
          </Button>
        </CardContent>
      </Card>

      {sectionId !== "" && (
        <Card>
          <CardHeader>
            <CardTitle>Section subjects</CardTitle>
            <CardDescription>Tap to take ownership; tap again to clear.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(sectionSubjects.data ?? []).map((ss) => {
              const subject = subjectMap.get(ss.subject_id);
              const ownedBySomeoneElse =
                ss.teacher_user_id !== null && ss.teacher_user_id !== undefined;
              return (
                <div
                  key={ss.id}
                  className="flex items-center justify-between rounded-md border border-saffron-pale px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-indigo-dark">{subject?.name ?? `Subject #${ss.subject_id}`}</p>
                    <p className="text-xs text-muted-foreground">
                      {ss.weekly_periods} periods/week · teacher_user_id = {ss.teacher_user_id ?? "unassigned"}
                    </p>
                  </div>
                  {ownedBySomeoneElse ? (
                    <Button variant="ghost" size="sm" onClick={() => clearSS.mutate(ss.id)}>
                      Clear
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => assignSS.mutate(ss.id)}>
                      Take
                    </Button>
                  )}
                </div>
              );
            })}
            {!sectionSubjects.data?.length && (
              <p className="text-sm text-muted-foreground">
                No subjects mapped to this section. Use the Curriculum page to wire them up first.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function WorkloadTab({ teacherId }: { teacherId: number }) {
  const wl = useQuery({ queryKey: ["workload", teacherId], queryFn: () => getWorkload(teacherId) });
  if (wl.isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!wl.data) return <p className="text-sm text-muted-foreground">No data.</p>;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Tile label="Periods/week" value={wl.data.weekly_periods_total} icon={BookOpenCheck} />
        <Tile label="Classes" value={wl.data.classes_handled} icon={Briefcase} />
        <Tile label="Subjects" value={wl.data.subjects_taught} icon={ClipboardList} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Schedule</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!wl.data.entries.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No assignments yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Class</th>
                  <th className="px-4 py-3">Section</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3 text-right">Periods/week</th>
                </tr>
              </thead>
              <tbody>
                {wl.data.entries.map((e) => (
                  <tr key={e.section_subject_id} className="border-b last:border-b-0">
                    <td className="px-6 py-2">{e.class_name}</td>
                    <td className="px-4 py-2">{e.section_name}</td>
                    <td className="px-4 py-2">{e.subject_name}</td>
                    <td className="px-4 py-2 text-right font-mono">{e.weekly_periods}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Tile({ label, value, icon: Icon }: { label: string; value: number; icon: any }) {
  return (
    <Card className="border-saffron-pale">
      <CardHeader className="pb-2">
        <CardDescription className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-saffron-dark">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </CardDescription>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function AttendanceTab({ teacherId }: { teacherId: number }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [day, setDay] = useState(today);
  const list = useQuery({
    queryKey: ["teacher-attendance", teacherId],
    queryFn: () => listAttendance(teacherId, { start: undefined }),
  });
  const upsert = useMutation({
    mutationFn: (status: AttendanceStatus) => upsertAttendance(teacherId, { date: day, status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher-attendance", teacherId] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Mark attendance</CardTitle>
          <CardDescription>Status for the picked day; idempotent.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label>Date</Label>
            <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="w-44" />
          </div>
          {(["present", "absent", "leave", "half_day"] as const).map((s) => (
            <Button
              key={s}
              variant={s === "present" ? "default" : "outline"}
              onClick={() => upsert.mutate(s)}
              disabled={upsert.isPending}
            >
              {s.replace("_", " ")}
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nothing recorded yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((row) => (
                <li key={row.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <span className="font-mono text-xs">{row.date}</span>
                  <span className="font-medium uppercase tracking-wider text-saffron-darker">
                    {row.status.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-muted-foreground">{row.remarks ?? ""}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
