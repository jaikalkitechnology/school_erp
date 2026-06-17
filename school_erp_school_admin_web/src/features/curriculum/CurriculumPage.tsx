import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  listAcademicYears,
  listClasses,
  listSections,
  listSubjects,
  type AcademicYear,
  type ClassDef,
  type Section,
  type Subject,
} from "@/features/setup/api";
import {
  addChapter,
  bulkLinkSectionSubjects,
  createEvent,
  createHouse,
  createSyllabus,
  deleteEvent,
  deleteHouse,
  deleteSectionSubject,
  deleteSyllabus,
  listEvents,
  listHouses,
  listSectionSubjects,
  listSyllabi,
  setChapterProgress,
  type CalendarKind,
  type Chapter,
  type Syllabus,
} from "./api";

const TABS = ["Houses", "Section subjects", "Calendar", "Syllabus"] as const;
type Tab = (typeof TABS)[number];

export function CurriculumPage() {
  const [tab, setTab] = useState<Tab>("Houses");

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 5 · Academic</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Curriculum &amp; calendar</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Houses, the section→subject map, the academic calendar, and chapter-level syllabus tracking.
        </p>
      </header>

      <nav className="flex gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label
                ? "border-b-2 border-saffron text-saffron-darker"
                : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "Houses" && <HousesPanel />}
      {tab === "Section subjects" && <SectionSubjectsPanel />}
      {tab === "Calendar" && <CalendarPanel />}
      {tab === "Syllabus" && <SyllabusPanel />}
    </div>
  );
}

// ---- Houses ---------------------------------------------------------------

function HousesPanel() {
  const qc = useQueryClient();
  const houses = useQuery({ queryKey: ["houses"], queryFn: listHouses });
  const create = useMutation({
    mutationFn: createHouse,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["houses"] }),
  });
  const remove = useMutation({
    mutationFn: deleteHouse,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["houses"] }),
  });

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [color, setColor] = useState("#E85D2E");
  const [motto, setMotto] = useState("");

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Houses</CardTitle>
          <CardDescription>House captains can be assigned in Phase 7 once teachers exist.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {houses.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : !houses.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No houses yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {houses.data.map((h) => (
                <li key={h.id} className="flex items-center gap-3 px-6 py-3">
                  <span className="block h-8 w-8 rounded-full border" style={{ background: h.color }} />
                  <div className="flex-1">
                    <p className="font-medium text-indigo-dark">
                      {h.name} <span className="ml-2 font-mono text-xs text-saffron-dark">{h.code ?? ""}</span>
                    </p>
                    {h.motto && <p className="text-xs text-muted-foreground">{h.motto}</p>}
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => remove.mutate(h.id)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Add house</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FieldText label="Name" value={name} onChange={setName} placeholder="e.g. Saffron" />
          <FieldText label="Code" value={code} onChange={setCode} placeholder="S / R / B" />
          <div className="space-y-1.5">
            <Label>Color</Label>
            <div className="flex gap-2">
              <Input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-11 w-20 p-1" />
              <Input value={color} onChange={(e) => setColor(e.target.value)} />
            </div>
          </div>
          <FieldText label="Motto" value={motto} onChange={setMotto} />
          <Button
            disabled={!name || create.isPending}
            onClick={() =>
              create.mutate(
                { name, code: code || null, color, motto: motto || null },
                { onSuccess: () => { setName(""); setCode(""); setMotto(""); } },
              )
            }
          >
            <Plus className="h-4 w-4" />
            Add house
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Section subjects ------------------------------------------------------

function SectionSubjectsPanel() {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const [sectionId, setSectionId] = useState<number | "">("");
  const links = useQuery({
    queryKey: ["section-subjects", sectionId || null],
    queryFn: () => listSectionSubjects(sectionId === "" ? undefined : Number(sectionId)),
    enabled: sectionId !== "",
  });

  const link = useMutation({
    mutationFn: ({ sec, subjs }: { sec: number; subjs: number[] }) => bulkLinkSectionSubjects(sec, subjs, 4),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["section-subjects"] }),
  });
  const remove = useMutation({
    mutationFn: deleteSectionSubject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["section-subjects"] }),
  });

  const sectionLabel = (s: Section) => {
    const cls = classes.data?.find((c) => c.id === s.class_def_id);
    return `${cls?.name ?? "?"} · ${s.name}`;
  };

  const linkedIds = new Set((links.data ?? []).map((ss) => ss.subject_id));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick a section</CardTitle>
          <CardDescription>Assign subjects taught in that section.</CardDescription>
        </CardHeader>
        <CardContent>
          <select
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">— pick a section —</option>
            {(sections.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>{sectionLabel(s)}</option>
            ))}
          </select>
        </CardContent>
      </Card>

      {sectionId !== "" && (
        <Card>
          <CardHeader>
            <CardTitle>Subjects in this section</CardTitle>
            <CardDescription>Click a subject to toggle it on/off.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
              {(subjects.data ?? []).map((sub: Subject) => {
                const linked = linkedIds.has(sub.id);
                const linkRow = (links.data ?? []).find((ss) => ss.subject_id === sub.id);
                return (
                  <button
                    key={sub.id}
                    type="button"
                    className={cn(
                      "rounded-md border p-3 text-left transition-colors",
                      linked
                        ? "border-saffron bg-saffron-pale text-saffron-darker"
                        : "border-border hover:border-saffron-light",
                    )}
                    onClick={() => {
                      if (linked && linkRow) {
                        remove.mutate(linkRow.id);
                      } else {
                        link.mutate({ sec: Number(sectionId), subjs: [sub.id] });
                      }
                    }}
                  >
                    <p className="font-medium">{sub.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {sub.code} · {linked ? `${linkRow?.weekly_periods ?? 4} periods/wk` : "tap to add"}
                    </p>
                  </button>
                );
              })}
            </div>
            {!subjects.data?.length && (
              <p className="text-sm text-muted-foreground">
                No subjects yet — add them on the Org page first.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Calendar -------------------------------------------------------------

const KIND_TONE: Record<CalendarKind, string> = {
  general: "bg-saffron-pale text-saffron-darker",
  exam: "bg-marigold-pale text-marigold-dark",
  sports: "bg-teal-pale text-teal-dark",
  cultural: "bg-marigold-pale text-marigold-dark",
  parent_teacher: "bg-saffron-pale text-saffron-darker",
  holiday: "bg-muted text-muted-foreground",
};

function CalendarPanel() {
  const qc = useQueryClient();
  const events = useQuery({ queryKey: ["events"], queryFn: () => listEvents() });
  const create = useMutation({
    mutationFn: createEvent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });
  const remove = useMutation({
    mutationFn: deleteEvent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });

  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<CalendarKind>("general");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [allDay, setAllDay] = useState(true);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>New event</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-2 gap-3 lg:grid-cols-5"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(
                { title, kind, starts_at: startsAt, ends_at: endsAt || null, is_all_day: allDay },
                { onSuccess: () => { setTitle(""); setStartsAt(""); setEndsAt(""); } },
              );
            }}
          >
            <FieldText label="Title" value={title} onChange={setTitle} />
            <div className="space-y-1.5">
              <Label>Kind</Label>
              <select
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={kind}
                onChange={(e) => setKind(e.target.value as CalendarKind)}
              >
                <option value="general">General</option>
                <option value="exam">Exam</option>
                <option value="sports">Sports</option>
                <option value="cultural">Cultural</option>
                <option value="parent_teacher">Parent-Teacher</option>
                <option value="holiday">Holiday</option>
              </select>
            </div>
            <FieldDate label="Starts" value={startsAt} onChange={setStartsAt} />
            <FieldDate label="Ends" value={endsAt} onChange={setEndsAt} />
            <div className="flex items-end gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={allDay}
                  onChange={(e) => setAllDay(e.target.checked)}
                  className="h-4 w-4 accent-saffron"
                />
                All day
              </label>
            </div>
            <div className="col-span-2 lg:col-span-5 flex justify-end">
              <Button type="submit" disabled={!title || !startsAt}>
                <Plus className="h-4 w-4" />
                Add event
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Events ({events.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!events.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No events yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {events.data.map((e) => (
                <li key={e.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium text-indigo-dark">{e.title}</p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-mono">
                        {new Date(e.starts_at).toLocaleString()}
                        {e.ends_at && ` → ${new Date(e.ends_at).toLocaleString()}`}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wider", KIND_TONE[e.kind])}>
                      {e.kind.replace(/_/g, " ")}
                    </span>
                    <Button variant="ghost" size="icon" onClick={() => remove.mutate(e.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Syllabus -------------------------------------------------------------

function SyllabusPanel() {
  const qc = useQueryClient();
  const years = useQuery({ queryKey: ["academic-years"], queryFn: listAcademicYears });
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const [yearId, setYearId] = useState<number | "">("");
  const [classId, setClassId] = useState<number | "">("");
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [title, setTitle] = useState("");

  const filterParams = {
    year_id: yearId === "" ? undefined : Number(yearId),
    class_def_id: classId === "" ? undefined : Number(classId),
    subject_id: subjectId === "" ? undefined : Number(subjectId),
  };
  const syllabi = useQuery({
    queryKey: ["syllabi", filterParams],
    queryFn: () => listSyllabi(filterParams),
  });

  const create = useMutation({
    mutationFn: () =>
      createSyllabus({
        year_id: Number(yearId),
        class_def_id: Number(classId),
        subject_id: Number(subjectId),
        title,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["syllabi"] });
      setTitle("");
    },
  });
  const remove = useMutation({
    mutationFn: deleteSyllabus,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["syllabi"] }),
  });

  const yearOpts = years.data ?? [];
  const classOpts = classes.data ?? [];
  const subjectOpts = subjects.data ?? [];

  const canCreate = yearId !== "" && classId !== "" && subjectId !== "" && title;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick a slice</CardTitle>
          <CardDescription>Year → class → subject filters the syllabus list and seeds the new-syllabus form.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-4">
            <SelectField label="Year" value={yearId} onChange={setYearId} options={yearOpts.map((y: AcademicYear) => ({ value: y.id, label: y.name }))} />
            <SelectField label="Class" value={classId} onChange={setClassId} options={classOpts.map((c: ClassDef) => ({ value: c.id, label: c.name }))} />
            <SelectField label="Subject" value={subjectId} onChange={setSubjectId} options={subjectOpts.map((s: Subject) => ({ value: s.id, label: s.name }))} />
            <div className="space-y-1.5">
              <Label>Syllabus title</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Math 5 · 2025-26" />
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <Button disabled={!canCreate || create.isPending} onClick={() => create.mutate()}>
              <Plus className="h-4 w-4" />
              Create syllabus
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {syllabi.data?.map((s) => (
          <SyllabusRow key={s.id} syllabus={s} onDelete={() => remove.mutate(s.id)} />
        ))}
        {syllabi.isSuccess && !syllabi.data?.length && (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              No syllabus matches this filter yet.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function SyllabusRow({ syllabus, onDelete }: { syllabus: Syllabus; onDelete: () => void }) {
  const qc = useQueryClient();
  const newChapter = useMutation({
    mutationFn: ({ syllabus_id, payload }: { syllabus_id: number; payload: any }) =>
      addChapter(syllabus_id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["syllabi"] }),
  });
  const setProgress = useMutation({
    mutationFn: ({ chapter_id, pct }: { chapter_id: number; pct: number }) =>
      setChapterProgress(chapter_id, pct),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["syllabi"] }),
  });

  const [title, setTitle] = useState("");
  const [periods, setPeriods] = useState(4);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{syllabus.title}</CardTitle>
            <CardDescription>
              {syllabus.chapters.length} chapter{syllabus.chapters.length !== 1 && "s"} ·{" "}
              <span className="font-mono text-saffron-dark">{Number(syllabus.overall_completion_pct).toFixed(1)}%</span>
              {" "}complete
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={onDelete}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          {syllabus.chapters.map((c: Chapter) => (
            <div key={c.id} className="grid grid-cols-[40px_1fr_120px_100px] items-center gap-3 rounded-md border border-saffron-pale px-3 py-2 text-sm">
              <span className="font-mono text-xs text-muted-foreground">{c.sequence}</span>
              <span>
                <p className="font-medium text-indigo-dark">{c.title}</p>
                <p className="text-xs text-muted-foreground">{c.expected_periods} periods{c.completed_on ? ` · done ${c.completed_on}` : ""}</p>
              </span>
              <span className="h-2 rounded-full bg-muted">
                <span
                  className="block h-full rounded-full bg-saffron"
                  style={{ width: `${Math.min(100, Number(c.completion_pct) || 0)}%` }}
                />
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step={5}
                value={Number(c.completion_pct) || 0}
                onChange={(e) =>
                  setProgress.mutate({ chapter_id: c.id, pct: Math.max(0, Math.min(100, Number(e.target.value))) })
                }
                className="h-9 rounded-md border border-input bg-background px-2 text-right text-xs font-mono"
              />
            </div>
          ))}
          {!syllabus.chapters.length && (
            <p className="text-xs text-muted-foreground">No chapters yet.</p>
          )}
        </div>
        <form
          className="flex flex-wrap items-end gap-2 rounded-md border border-dashed border-saffron-pale p-2 text-sm"
          onSubmit={(e) => {
            e.preventDefault();
            newChapter.mutate(
              {
                syllabus_id: syllabus.id,
                payload: { sequence: syllabus.chapters.length + 1, title, expected_periods: periods },
              },
              { onSuccess: () => { setTitle(""); setPeriods(4); } },
            );
          }}
        >
          <Input placeholder="Chapter title" value={title} onChange={(e) => setTitle(e.target.value)} className="min-w-[200px] flex-1" />
          <Input
            type="number"
            min={1}
            max={50}
            value={periods}
            onChange={(e) => setPeriods(Math.max(1, Number(e.target.value)))}
            className="w-24"
          />
          <Button size="sm" type="submit" disabled={!title}>
            <Plus className="h-3.5 w-3.5" />
            Add chapter
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ---- shared ---------------------------------------------------------------

function FieldText({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function FieldDate({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="datetime-local" value={value} onChange={(e) => onChange(e.target.value)} />
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
  value: number | "";
  onChange: (v: number | "") => void;
  options: { value: number; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}
      >
        <option value="">— any —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
