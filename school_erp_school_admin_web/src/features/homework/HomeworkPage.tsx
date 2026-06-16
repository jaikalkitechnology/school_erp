import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Eye, FileText, Paperclip, Plus, Star, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { listClasses, listSections, listSubjects } from "@/features/setup/api";
import {
  createHomework,
  deleteHomework,
  grade,
  homeworkReport,
  listHomework,
  submissionsFor,
  type Submission,
  type SubmissionStatus,
} from "./api";

const STATUS_TONE: Record<SubmissionStatus, string> = {
  submitted: "bg-teal-pale text-teal-dark",
  graded: "bg-saffron-pale text-saffron-darker",
  late: "bg-marigold-pale text-marigold-dark",
  missing: "bg-destructive/15 text-destructive",
};

export function HomeworkPage() {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const [sectionId, setSectionId] = useState<number | "">("");
  const list = useQuery({
    queryKey: ["homework", sectionId],
    queryFn: () => listHomework({ section_id: Number(sectionId) }),
    enabled: sectionId !== "",
  });

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );
  const subjectMap = useMemo(
    () => new Map((subjects.data ?? []).map((s) => [s.id, s])),
    [subjects.data],
  );

  const today = new Date().toISOString().slice(0, 10);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newSubjectId, setNewSubjectId] = useState<number | "">("");
  const [newDue, setNewDue] = useState(today);
  const [newMax, setNewMax] = useState(10);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      createHomework({
        section_id: Number(sectionId),
        subject_id: newSubjectId === "" ? undefined : Number(newSubjectId),
        title: newTitle,
        description: newDescription || undefined,
        due_date: newDue,
        max_marks: newMax,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["homework", sectionId] });
      setNewTitle("");
      setNewDescription("");
    },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Could not create homework"),
  });

  const remove = useMutation({
    mutationFn: deleteHomework,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["homework", sectionId] }),
  });

  const [activeId, setActiveId] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 14 · Homework</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Homework &amp; assignments</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Create homework per section, see who's submitted, and grade.
        </p>
      </header>

      <Card>
        <CardHeader><CardTitle>Pick a section</CardTitle></CardHeader>
        <CardContent>
          <select
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={sectionId}
            onChange={(e) => { setSectionId(e.target.value ? Number(e.target.value) : ""); setActiveId(null); }}
          >
            <option value="">— pick a section —</option>
            {(sections.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {classMap.get(s.class_def_id) ?? "?"} · Section {s.name}
              </option>
            ))}
          </select>
        </CardContent>
      </Card>

      {sectionId !== "" && (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><Plus className="h-5 w-5" /> New homework</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Field label="Title" value={newTitle} onChange={setNewTitle} />
              <div className="space-y-1.5">
                <Label>Description</Label>
                <textarea
                  className="min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label>Subject</Label>
                  <select
                    className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={newSubjectId}
                    onChange={(e) => setNewSubjectId(e.target.value ? Number(e.target.value) : "")}
                  >
                    <option value="">— optional —</option>
                    {(subjects.data ?? []).map((s) => (
                      <option key={s.id} value={s.id}>{s.code}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label>Due date</Label>
                  <Input type="date" value={newDue} onChange={(e) => setNewDue(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>Max marks</Label>
                  <Input type="number" value={newMax} onChange={(e) => setNewMax(Number(e.target.value) || 0)} />
                </div>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button onClick={() => { setError(null); create.mutate(); }} disabled={!newTitle || create.isPending}>
                <Plus className="h-4 w-4" /> Create
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Existing homework</CardTitle></CardHeader>
            <CardContent className="p-0">
              {!list.data?.length ? (
                <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet.</p>
              ) : (
                <ul className="divide-y divide-saffron-pale">
                  {list.data.map((hw) => (
                    <li
                      key={hw.id}
                      className={cn(
                        "px-6 py-3 text-sm cursor-pointer",
                        activeId === hw.id && "bg-saffron-pale/40",
                      )}
                      onClick={() => setActiveId(hw.id)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="truncate font-medium text-indigo-dark">{hw.title}</p>
                            {(hw.attachments?.length ?? 0) > 0 && (
                              <span
                                className="inline-flex shrink-0 items-center gap-1 rounded-full bg-teal-pale px-2 py-0.5 text-[10px] font-semibold text-teal-dark"
                                title={`${hw.attachments.length} worksheet attachment${hw.attachments.length === 1 ? "" : "s"}`}
                              >
                                <Paperclip className="h-2.5 w-2.5" />
                                {hw.attachments.length}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Due {hw.due_date} · max {hw.max_marks}
                            {hw.subject_id && ` · ${subjectMap.get(hw.subject_id)?.code ?? ""}`}
                          </p>
                          {hw.description && (
                            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                              {hw.description}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="View details"
                            onClick={(e) => { e.stopPropagation(); setActiveId(hw.id); }}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete"
                            onClick={(e) => { e.stopPropagation(); remove.mutate(hw.id); }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeId && (() => {
        const activeHw = list.data?.find((h) => h.id === activeId);
        return (
          <HomeworkDetail
            homeworkId={activeId}
            homework={activeHw}
            subjectCode={
              activeHw?.subject_id
                ? subjectMap.get(activeHw.subject_id)?.code
                : undefined
            }
          />
        );
      })()}
    </div>
  );
}

function HomeworkDetail({
  homeworkId,
  homework,
  subjectCode,
}: {
  homeworkId: number;
  homework?: import("./api").Homework;
  subjectCode?: string;
}) {
  const qc = useQueryClient();
  const report = useQuery({
    queryKey: ["homework-report", homeworkId],
    queryFn: () => homeworkReport(homeworkId),
  });
  const submissions = useQuery({
    queryKey: ["homework-subs", homeworkId],
    queryFn: () => submissionsFor(homeworkId),
  });

  const submissionByStudent = useMemo(
    () => new Map((submissions.data ?? []).map((s) => [s.student_id, s])),
    [submissions.data],
  );

  const gradeMut = useMutation({
    mutationFn: ({ id, marks, feedback }: { id: number; marks: number; feedback?: string }) =>
      grade(id, { marks, feedback }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["homework-report", homeworkId] });
      qc.invalidateQueries({ queryKey: ["homework-subs", homeworkId] });
    },
  });

  if (!report.data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">Loading…</CardContent>
      </Card>
    );
  }

  const maxMarks = Number(report.data.max_marks ?? 100) || 100;
  const description = homework?.description ?? null;
  const attachments = homework?.attachments ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5" /> {report.data.title}
        </CardTitle>
        <CardDescription>
          {report.data.submitted_count} / {report.data.total_students} submitted · due {report.data.due_date} · max {maxMarks}
          {subjectCode && ` · ${subjectCode}`}
        </CardDescription>
      </CardHeader>
      {(description || attachments.length > 0) && (
        <div className="border-t bg-saffron-pale/30 px-6 py-4">
          {description && (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Instructions
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-indigo-dark">{description}</p>
            </div>
          )}
          {attachments.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Worksheet attachments ({attachments.length})
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {attachments.map((p) => (
                  <AttachmentChip key={p} path={p} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <CardContent className="p-0">
        {report.data.rows.length === 0 && (
          <p className="border-y bg-muted/30 px-6 py-4 text-sm text-muted-foreground">
            No students in this section yet — admit students or move them
            into the section before submissions can come in.
          </p>
        )}
        <table className="w-full text-sm">
          <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-6 py-3">Student</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submission</th>
              <th className="px-4 py-3">Marks</th>
              <th className="px-6 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {report.data.rows.map((row) => {
              const sub = submissionByStudent.get(row.student_id);
              return (
                <tr key={row.student_id} className="border-b last:border-b-0 align-top">
                  <td className="px-6 py-3">
                    <p className="font-medium text-indigo-dark">{row.full_name}</p>
                    <p className="font-mono text-xs text-muted-foreground">{row.admission_number}</p>
                  </td>
                  <td className="px-4 py-3">
                    {row.status ? (
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wider", STATUS_TONE[row.status])}>
                        {row.status}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">pending</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <SubmissionCell sub={sub} submittedAt={row.submitted_at} />
                  </td>
                  <td className="px-4 py-3 font-mono">{row.marks ?? "—"}</td>
                  <td className="px-6 py-3 text-right">
                    {sub && sub.status !== "graded" ? (
                      <GradeInline
                        max={maxMarks}
                        onSubmit={(marks, feedback) => gradeMut.mutate({ id: sub.id, marks, feedback })}
                      />
                    ) : sub && sub.status === "graded" ? (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Star className="h-3 w-3 text-marigold" />
                        graded
                      </span>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function SubmissionCell({
  sub,
  submittedAt,
}: {
  sub: Submission | undefined;
  submittedAt: string | null;
}) {
  if (!sub) {
    return <span className="font-mono text-xs text-muted-foreground">—</span>;
  }
  return (
    <div className="space-y-1.5">
      <p className="font-mono text-xs text-muted-foreground">
        {submittedAt ? new Date(submittedAt).toLocaleString() : "—"}
      </p>
      {sub.content && (
        <p className="max-w-sm whitespace-pre-wrap text-xs text-indigo-dark">{sub.content}</p>
      )}
      {sub.attachments?.length ? (
        <div className="flex flex-wrap gap-1">
          {sub.attachments.map((path) => (
            <AttachmentChip key={path} path={path} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Fetches a tenant-scoped upload via the authed axios client, then opens it
 * in a new tab via a blob URL. We can't just put the path in an <a href>
 * because the file-serving endpoint requires the Authorization + tenant
 * headers that only the axios interceptor knows about.
 */
function AttachmentChip({ path }: { path: string }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filename = path.split("/").pop() ?? path;
  const isImage = /\.(jpe?g|png|gif|webp)$/i.test(filename);

  const open = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Blob>(`/v1/uploads/${path}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e: any) {
      // Surface the real reason instead of pretending nothing happened.
      // Detail comes back as a Blob when responseType is "blob", so we
      // have to read it back to a string.
      const status = e?.response?.status;
      let detail = e?.message ?? "Could not open file";
      const blob = e?.response?.data;
      if (blob instanceof Blob) {
        try {
          const text = await blob.text();
          try { detail = JSON.parse(text)?.detail ?? text; } catch { detail = text; }
        } catch { /* keep fallback */ }
      } else if (typeof blob === "object" && blob?.detail) {
        detail = blob.detail;
      }
      setError(status ? `${status}: ${detail}` : detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-start gap-0.5">
      <button
        type="button"
        onClick={open}
        disabled={loading}
        className="inline-flex max-w-[180px] items-center gap-1 truncate rounded-md border border-saffron-pale bg-saffron-pale/30 px-2 py-1 text-[11px] text-indigo-dark hover:bg-saffron-pale disabled:opacity-50"
        title={filename}
      >
        {isImage ? <Paperclip className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
        <span className="truncate">{filename}</span>
      </button>
      {error && (
        <span className="max-w-[200px] truncate text-[10px] text-destructive" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}

function GradeInline({ max, onSubmit }: { max: number; onSubmit: (marks: number, feedback?: string) => void }) {
  const [marks, setMarks] = useState(0);
  const [feedback, setFeedback] = useState("");
  return (
    <span className="inline-flex items-center gap-2">
      <Input
        type="number"
        min={0}
        max={max}
        value={marks}
        onChange={(e) => {
          const n = Number(e.target.value) || 0;
          setMarks(Math.max(0, Math.min(max, n)));
        }}
        className="h-8 w-20"
      />
      <span className="text-xs text-muted-foreground">/{max}</span>
      <Input
        placeholder="feedback"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        className="h-8 w-40"
      />
      <Button size="sm" onClick={() => onSubmit(marks, feedback || undefined)}>
        Grade
      </Button>
    </span>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
