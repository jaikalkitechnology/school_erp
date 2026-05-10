import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, BookOpenCheck, ListChecks, Plus, Save, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections, listSubjects } from "@/features/setup/api";
import {
  bulkMarks,
  createExam,
  examResults,
  examRoster,
  listExamSubjects,
  listExams,
  listGradeScales,
  publishExam,
  scheduleSubject,
  upsertGradeScale,
  type ExamType,
  type ExamStatus,
  type MarkStatus,
  type RosterRow,
} from "./api";

const TABS = ["Exams", "Marks entry", "Results", "Grade scale"] as const;
type Tab = (typeof TABS)[number];

const STATUS_TONE: Record<ExamStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  scheduled: "bg-marigold-pale text-marigold-dark",
  in_progress: "bg-saffron-pale text-saffron-darker",
  completed: "bg-saffron-pale text-saffron-darker",
  published: "bg-teal-pale text-teal-dark",
};

const MARK_TONE: Record<MarkStatus, string> = {
  pass: "bg-teal-pale text-teal-dark",
  fail: "bg-destructive/15 text-destructive",
  absent: "bg-muted text-muted-foreground",
  exempt: "bg-saffron-pale text-saffron-darker",
};

export function ExamsPage() {
  const [tab, setTab] = useState<Tab>("Exams");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 15 · Examinations</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Exam system</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Schedule exams, enter marks per section, manage your grade scale, and review per-section
          results with auto-rank.
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
              tab === label ? "border-b-2 border-saffron text-saffron-darker" : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "Exams" && <ExamsPanel />}
      {tab === "Marks entry" && <MarksPanel />}
      {tab === "Results" && <ResultsPanel />}
      {tab === "Grade scale" && <GradeScalePanel />}
    </div>
  );
}

// ---- Exams ---------------------------------------------------------------

function ExamsPanel() {
  const qc = useQueryClient();
  const exams = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const [name, setName] = useState("");
  const [kind, setKind] = useState<ExamType>("unit_test");
  const [maxMarks, setMaxMarks] = useState(100);

  const create = useMutation({
    mutationFn: () => createExam({ name, kind, default_max_marks: maxMarks }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exams"] });
      setName("");
    },
  });
  const publish = useMutation({
    mutationFn: publishExam,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exams"] }),
  });

  const [activeExamId, setActiveExamId] = useState<number | null>(null);
  const exam = exams.data?.find((e) => e.id === activeExamId) ?? null;
  const examSubjects = useQuery({
    queryKey: ["exam-subjects", activeExamId],
    queryFn: () => listExamSubjects(activeExamId!),
    enabled: activeExamId !== null,
  });

  const [classDefId, setClassDefId] = useState<number | "">("");
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [examMax, setExamMax] = useState(50);
  const [passing, setPassing] = useState(18);
  const schedule = useMutation({
    mutationFn: () =>
      scheduleSubject(activeExamId!, {
        class_def_id: Number(classDefId),
        subject_id: Number(subjectId),
        max_marks: examMax,
        passing_marks: passing,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exam-subjects", activeExamId] }),
  });

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );
  const subjectMap = useMemo(
    () => new Map((subjects.data ?? []).map((s) => [s.id, s])),
    [subjects.data],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Plus className="h-5 w-5" /> New exam</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Field label="Name" value={name} onChange={setName} placeholder="Unit Test 1" />
          <div className="space-y-1.5">
            <Label>Kind</Label>
            <select className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm" value={kind} onChange={(e) => setKind(e.target.value as ExamType)}>
              <option value="unit_test">Unit Test</option>
              <option value="quarterly">Quarterly</option>
              <option value="half_yearly">Half-yearly</option>
              <option value="annual">Annual</option>
              <option value="other">Other</option>
            </select>
          </div>
          <FieldNum label="Default max marks" value={maxMarks} onChange={setMaxMarks} />
          <Button onClick={() => create.mutate()} disabled={!name || create.isPending}>
            <Plus className="h-4 w-4" /> Create
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Existing exams ({exams.data?.length ?? 0})</CardTitle></CardHeader>
        <CardContent className="p-0">
          {!exams.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No exams yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {exams.data.map((e) => (
                <li
                  key={e.id}
                  className={cn("px-6 py-3 text-sm cursor-pointer", activeExamId === e.id && "bg-saffron-pale/40")}
                  onClick={() => setActiveExamId(e.id)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-indigo-dark">{e.name}</p>
                      <p className="text-xs text-muted-foreground">{e.kind} · max {e.default_max_marks}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase", STATUS_TONE[e.status])}>
                        {e.status}
                      </span>
                      {e.status !== "published" && (
                        <Button size="sm" variant="ghost" onClick={(ev) => { ev.stopPropagation(); publish.mutate(e.id); }}>
                          <Send className="h-3 w-3" /> Publish
                        </Button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {exam && (
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BookOpenCheck className="h-5 w-5" /> {exam.name} — schedule</CardTitle>
            <CardDescription>Add a (class × subject) row with its max + passing marks.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 lg:grid-cols-5">
              <Select label="Class" value={classDefId} onChange={(v) => setClassDefId(v ? Number(v) : "")} options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))} />
              <Select label="Subject" value={subjectId} onChange={(v) => setSubjectId(v ? Number(v) : "")} options={(subjects.data ?? []).map((s) => ({ value: s.id, label: s.name }))} />
              <FieldNum label="Max" value={examMax} onChange={setExamMax} />
              <FieldNum label="Passing" value={passing} onChange={setPassing} />
              <div className="flex items-end">
                <Button disabled={classDefId === "" || subjectId === "" || schedule.isPending} onClick={() => schedule.mutate()}>
                  <Plus className="h-4 w-4" /> Schedule
                </Button>
              </div>
            </div>
            <ul className="divide-y divide-saffron-pale border-t border-saffron-pale">
              {(examSubjects.data ?? []).map((es) => (
                <li key={es.id} className="flex justify-between px-2 py-2 text-sm">
                  <span>{classMap.get(es.class_def_id)} · {subjectMap.get(es.subject_id)?.name ?? "?"}</span>
                  <span className="font-mono text-xs text-muted-foreground">max {es.max_marks} · pass {es.passing_marks}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Marks entry ---------------------------------------------------------

function MarksPanel() {
  const qc = useQueryClient();
  const exams = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const [examId, setExamId] = useState<number | "">("");
  const examSubjects = useQuery({
    queryKey: ["exam-subjects", examId || null],
    queryFn: () => listExamSubjects(Number(examId)),
    enabled: examId !== "",
  });

  const [examSubjectId, setExamSubjectId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const roster = useQuery({
    queryKey: ["exam-roster", examSubjectId, sectionId],
    queryFn: () => examRoster(Number(examSubjectId), Number(sectionId)),
    enabled: examSubjectId !== "" && sectionId !== "",
  });

  const [edits, setEdits] = useState<Record<number, RosterRow>>({});

  useEffect(() => {
    if (!roster.data) return;
    const m: Record<number, RosterRow> = {};
    for (const r of roster.data.rows) m[r.student_id] = r;
    setEdits(m);
  }, [roster.data]);

  const save = useMutation({
    mutationFn: () =>
      bulkMarks({
        exam_subject_id: Number(examSubjectId),
        entries: Object.values(edits).map((r) => ({
          student_id: r.student_id,
          obtained_marks: r.obtained_marks,
          status: r.status ?? undefined,
          remarks: r.remarks ?? undefined,
        })),
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["exam-roster", examSubjectId, sectionId] }),
  });

  const subjectMap = useMemo(
    () => new Map((subjects.data ?? []).map((s) => [s.id, s])),
    [subjects.data],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Pick exam subject + section</CardTitle></CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <Select label="Exam" value={examId} onChange={(v) => { setExamId(v ? Number(v) : ""); setExamSubjectId(""); }} options={(exams.data ?? []).map((e) => ({ value: e.id, label: e.name }))} />
          <Select
            label="Subject (class)"
            value={examSubjectId}
            onChange={(v) => setExamSubjectId(v ? Number(v) : "")}
            options={(examSubjects.data ?? []).map((es) => ({
              value: es.id,
              label: `${subjectMap.get(es.subject_id)?.name ?? "?"} · class ${es.class_def_id}`,
            }))}
          />
          <Select label="Section" value={sectionId} onChange={(v) => setSectionId(v ? Number(v) : "")} options={(sections.data ?? []).map((s) => ({ value: s.id, label: `Section #${s.id} (class ${s.class_def_id})` }))} />
        </CardContent>
      </Card>

      {roster.data && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Roster · max {roster.data.max_marks} · passing {roster.data.passing_marks}</CardTitle>
              <CardDescription>Leave blank to mark absent automatically.</CardDescription>
            </div>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              <Save className="h-4 w-4" />
              {save.isPending ? "Saving…" : "Save marks"}
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Student</th>
                  <th className="px-4 py-3">Obtained</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {roster.data.rows.map((row) => {
                  const edit = edits[row.student_id] ?? row;
                  return (
                    <tr key={row.student_id} className="border-b last:border-b-0">
                      <td className="px-6 py-2">{roster.data!.student_names[row.student_id]}</td>
                      <td className="px-4 py-2">
                        <Input
                          type="number"
                          value={edit.obtained_marks ?? ""}
                          onChange={(e) =>
                            setEdits((m) => ({
                              ...m,
                              [row.student_id]: {
                                ...edit,
                                obtained_marks: e.target.value === "" ? null : Number(e.target.value),
                              },
                            }))
                          }
                          className="h-8 w-24"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <select
                          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                          value={edit.status ?? ""}
                          onChange={(e) =>
                            setEdits((m) => ({
                              ...m,
                              [row.student_id]: {
                                ...edit,
                                status: (e.target.value || null) as MarkStatus | null,
                              },
                            }))
                          }
                        >
                          <option value="">auto</option>
                          <option value="pass">pass</option>
                          <option value="fail">fail</option>
                          <option value="absent">absent</option>
                          <option value="exempt">exempt</option>
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <Input
                          value={edit.remarks ?? ""}
                          onChange={(e) =>
                            setEdits((m) => ({
                              ...m,
                              [row.student_id]: { ...edit, remarks: e.target.value || null },
                            }))
                          }
                          className="h-8"
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Results -------------------------------------------------------------

function ResultsPanel() {
  const exams = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const [examId, setExamId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const results = useQuery({
    queryKey: ["exam-results", examId, sectionId],
    queryFn: () => examResults(Number(examId), Number(sectionId)),
    enabled: examId !== "" && sectionId !== "",
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Award className="h-5 w-5" /> Pick exam + section</CardTitle></CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-2">
          <Select label="Exam" value={examId} onChange={(v) => setExamId(v ? Number(v) : "")} options={(exams.data ?? []).map((e) => ({ value: e.id, label: e.name }))} />
          <Select label="Section" value={sectionId} onChange={(v) => setSectionId(v ? Number(v) : "")} options={(sections.data ?? []).map((s) => ({ value: s.id, label: `Section #${s.id} (class ${s.class_def_id})` }))} />
        </CardContent>
      </Card>

      {results.data && (
        <Card>
          <CardHeader>
            <CardTitle>Class average: {results.data.section_average_pct.toFixed(2)}%</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Rank</th>
                  <th className="px-4 py-3">Student</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">%</th>
                  <th className="px-4 py-3">Grade</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {results.data.students.map((s) => (
                  <tr key={s.student_id} className="border-b last:border-b-0">
                    <td className="px-6 py-2 font-mono">{s.rank_in_section ?? "—"}</td>
                    <td className="px-4 py-2">
                      <p className="font-medium text-indigo-dark">{s.full_name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{s.admission_number}</p>
                    </td>
                    <td className="px-4 py-2 font-mono">{s.total_obtained}/{s.total_max}</td>
                    <td className="px-4 py-2 font-mono">{s.percentage}%</td>
                    <td className="px-4 py-2 font-semibold">{s.overall_grade ?? "—"}</td>
                    <td className="px-4 py-2">
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase", MARK_TONE[s.overall_status])}>
                        {s.overall_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Grade scale ---------------------------------------------------------

function GradeScalePanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["grade-scales"], queryFn: listGradeScales });

  const [code, setCode] = useState("default");
  const [name, setName] = useState("Default scale");
  const [bands, setBands] = useState<{ min_pct: number; grade: string }[]>([
    { min_pct: 90, grade: "A+" },
    { min_pct: 75, grade: "A" },
    { min_pct: 50, grade: "B" },
    { min_pct: 33, grade: "C" },
    { min_pct: 0, grade: "F" },
  ]);
  const [isDefault, setIsDefault] = useState(true);

  useEffect(() => {
    const existing = list.data?.find((g) => g.code === code);
    if (existing) {
      setName(existing.name);
      setBands(existing.bands.map(({ min_pct, grade }) => ({ min_pct, grade })));
      setIsDefault(existing.is_default);
    }
  }, [list.data, code]);

  const save = useMutation({
    mutationFn: () => upsertGradeScale({ code, name, bands, is_default: isDefault }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grade-scales"] }),
  });

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2"><ListChecks className="h-5 w-5" /> Grade scale</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 lg:grid-cols-3">
          <Field label="Code" value={code} onChange={setCode} />
          <Field label="Name" value={name} onChange={setName} />
          <label className="flex items-end gap-2 text-sm">
            <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} className="h-4 w-4 accent-saffron" />
            Default for the school
          </label>
        </div>
        <table className="w-full text-sm">
          <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2">Min %</th>
              <th className="px-4 py-2">Grade</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {bands.map((b, i) => (
              <tr key={i} className="border-b last:border-b-0">
                <td className="px-4 py-2">
                  <Input
                    type="number"
                    value={b.min_pct}
                    onChange={(e) =>
                      setBands((arr) => arr.map((x, j) => (j === i ? { ...x, min_pct: Number(e.target.value) || 0 } : x)))
                    }
                    className="h-8 w-24"
                  />
                </td>
                <td className="px-4 py-2">
                  <Input
                    value={b.grade}
                    onChange={(e) =>
                      setBands((arr) => arr.map((x, j) => (j === i ? { ...x, grade: e.target.value } : x)))
                    }
                    className="h-8 w-24"
                  />
                </td>
                <td className="px-4 py-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => setBands((arr) => arr.filter((_, j) => j !== i))}>
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex justify-between">
          <Button variant="outline" size="sm" onClick={() => setBands((arr) => [...arr, { min_pct: 0, grade: "" }])}>
            <Plus className="h-4 w-4" /> Add band
          </Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            <Save className="h-4 w-4" /> Save scale
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---- shared bits ---------------------------------------------------------

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function FieldNum({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="number" value={value} onChange={(e) => onChange(Number(e.target.value) || 0)} />
    </div>
  );
}

function Select<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T | "";
  onChange: (v: string) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm" value={String(value)} onChange={(e) => onChange(e.target.value)}>
        <option value="">— pick —</option>
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
