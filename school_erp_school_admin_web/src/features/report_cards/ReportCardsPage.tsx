import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, Download, FileText, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import { listExams, examResults } from "@/features/exams/api";
import {
  generate,
  listCoCurricular,
  listSectionCards,
  listTemplates,
  pdfUrl,
  publishSection,
  upsertCoCurricular,
  upsertRemark,
  upsertTemplate,
  type Board,
  type ReportCardStatus,
} from "./api";

const TABS = ["Templates", "Co-curricular & remarks", "Generate", "Cards"] as const;
type Tab = (typeof TABS)[number];

const STATUS_TONE: Record<ReportCardStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  generated: "bg-marigold-pale text-marigold-dark",
  published: "bg-teal-pale text-teal-dark",
};

export function ReportCardsPage() {
  const [tab, setTab] = useState<Tab>("Templates");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 16 · Report cards
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Report cards</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Manage CBSE / ICSE / state templates, capture co-curricular grades + remarks,
          and bulk-generate PDF cards for any section.
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
      {tab === "Templates" && <TemplatesPanel />}
      {tab === "Co-curricular & remarks" && <CoCurricularPanel />}
      {tab === "Generate" && <GeneratePanel />}
      {tab === "Cards" && <CardsPanel />}
    </div>
  );
}

// ---- Templates -----------------------------------------------------------

function TemplatesPanel() {
  const qc = useQueryClient();
  const { data: templates = [] } = useQuery({
    queryKey: ["rc-templates"],
    queryFn: listTemplates,
  });
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [board, setBoard] = useState<Board>("cbse");
  const [isDefault, setIsDefault] = useState(true);

  const upsert = useMutation({
    mutationFn: () =>
      upsertTemplate({
        code,
        name,
        board,
        is_default: isDefault,
        layout: { show_co_curricular: true, show_attendance: true, show_remarks: true },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rc-templates"] });
      setCode("");
      setName("");
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Templates</CardTitle>
          <CardDescription>One default at a time; the default is used on bulk generate.</CardDescription>
        </CardHeader>
        <CardContent>
          {templates.length === 0 ? (
            <p className="text-sm text-muted-foreground">No templates yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {templates.map((t) => (
                <li key={t.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-indigo-dark">{t.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {t.code} · {t.board.toUpperCase()}
                    </p>
                  </div>
                  {t.is_default && (
                    <span className="rounded bg-teal-pale px-2 py-0.5 text-xs font-medium text-teal-dark">
                      Default
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Add / update template</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Code</Label>
              <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="cbse-default" />
            </div>
            <div>
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CBSE default" />
            </div>
            <div>
              <Label>Board</Label>
              <select
                className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={board}
                onChange={(e) => setBoard(e.target.value as Board)}
              >
                <option value="cbse">CBSE</option>
                <option value="icse">ICSE</option>
                <option value="state">State</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div className="flex items-end gap-2">
              <input
                id="rc-default"
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
              />
              <Label htmlFor="rc-default">Default</Label>
            </div>
          </div>
          <Button
            onClick={() => upsert.mutate()}
            disabled={!code || !name || upsert.isPending}
          >
            <Sparkles className="mr-1 h-4 w-4" />
            Save template
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Co-curricular + remarks --------------------------------------------

function CoCurricularPanel() {
  const qc = useQueryClient();
  const { data: exams = [] } = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: listClasses });

  const [examId, setExamId] = useState<number | null>(null);
  const [classId, setClassId] = useState<number | null>(null);
  const { data: sections = [] } = useQuery({
    queryKey: ["sections", classId],
    queryFn: () => (classId ? listSections(classId) : Promise.resolve([])),
    enabled: classId !== null,
  });
  const [sectionId, setSectionId] = useState<number | null>(null);

  const { data: results } = useQuery({
    queryKey: ["exam-results", examId, sectionId],
    queryFn: () => examResults(examId!, sectionId!),
    enabled: examId !== null && sectionId !== null,
  });
  const { data: ccList = [] } = useQuery({
    queryKey: ["co-curricular", examId, sectionId],
    queryFn: () => listCoCurricular(examId!, sectionId!),
    enabled: examId !== null && sectionId !== null,
  });

  const [area, setArea] = useState("Discipline");
  const [grade, setGrade] = useState("A");
  const [studentId, setStudentId] = useState<number | null>(null);
  const [teacherRemark, setTeacherRemark] = useState("");
  const [principalRemark, setPrincipalRemark] = useState("");

  const saveCC = useMutation({
    mutationFn: () =>
      upsertCoCurricular(examId!, { student_id: studentId!, area, grade }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["co-curricular", examId, sectionId] }),
  });
  const saveRemark = useMutation({
    mutationFn: () =>
      upsertRemark(examId!, {
        student_id: studentId!,
        teacher_remark: teacherRemark || undefined,
        principal_remark: principalRemark || undefined,
      }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick exam + section</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <div>
            <Label>Exam</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={examId ?? ""}
              onChange={(e) => setExamId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select…</option>
              {exams.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Class</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={classId ?? ""}
              onChange={(e) => {
                setClassId(e.target.value ? Number(e.target.value) : null);
                setSectionId(null);
              }}
            >
              <option value="">Select…</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Section</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={sectionId ?? ""}
              onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : null)}
              disabled={classId === null}
            >
              <option value="">Select…</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {results && (
        <Card>
          <CardHeader>
            <CardTitle>Add co-curricular grade</CardTitle>
            <CardDescription>Picks one student in this section, one area at a time.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-4 gap-3">
            <div>
              <Label>Student</Label>
              <select
                className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={studentId ?? ""}
                onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select…</option>
                {results.students.map((s) => (
                  <option key={s.student_id} value={s.student_id}>{s.full_name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label>Area</Label>
              <Input value={area} onChange={(e) => setArea(e.target.value)} />
            </div>
            <div>
              <Label>Grade</Label>
              <Input value={grade} onChange={(e) => setGrade(e.target.value)} />
            </div>
            <div className="flex items-end">
              <Button
                onClick={() => saveCC.mutate()}
                disabled={!studentId || !area || !grade || saveCC.isPending}
              >
                Save
              </Button>
            </div>
          </CardContent>
          <CardContent>
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Existing</p>
            {ccList.length === 0 ? (
              <p className="text-sm text-muted-foreground">No co-curricular grades yet.</p>
            ) : (
              <ul className="divide-y divide-saffron-pale">
                {ccList.map((c) => {
                  const stu = results.students.find((s) => s.student_id === c.student_id);
                  return (
                    <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{stu?.full_name ?? c.student_id}</span>
                      <span className="text-muted-foreground">{c.area}</span>
                      <span className="rounded bg-teal-pale px-2 py-0.5 text-teal-dark">{c.grade}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {results && (
        <Card>
          <CardHeader>
            <CardTitle>Remarks</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Student</Label>
              <select
                className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={studentId ?? ""}
                onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select…</option>
                {results.students.map((s) => (
                  <option key={s.student_id} value={s.student_id}>{s.full_name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label>Class teacher remark</Label>
              <textarea
                className="min-h-[80px] w-full rounded border border-input bg-transparent p-2 text-sm"
                value={teacherRemark}
                onChange={(e) => setTeacherRemark(e.target.value)}
              />
            </div>
            <div>
              <Label>Principal remark</Label>
              <textarea
                className="min-h-[80px] w-full rounded border border-input bg-transparent p-2 text-sm"
                value={principalRemark}
                onChange={(e) => setPrincipalRemark(e.target.value)}
              />
            </div>
            <div>
              <Button onClick={() => saveRemark.mutate()} disabled={!studentId || saveRemark.isPending}>
                Save remarks
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Generate ------------------------------------------------------------

function GeneratePanel() {
  const qc = useQueryClient();
  const { data: exams = [] } = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const { data: templates = [] } = useQuery({ queryKey: ["rc-templates"], queryFn: listTemplates });
  const [examId, setExamId] = useState<number | null>(null);
  const [classId, setClassId] = useState<number | null>(null);
  const { data: sections = [] } = useQuery({
    queryKey: ["sections", classId],
    queryFn: () => (classId ? listSections(classId) : Promise.resolve([])),
    enabled: classId !== null,
  });
  const [sectionId, setSectionId] = useState<number | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [publish, setPublish] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () =>
      generate({
        exam_id: examId!,
        section_id: sectionId!,
        template_id: templateId ?? undefined,
        publish,
      }),
    onSuccess: (res) => {
      setFlash(`Generated ${res.generated}, skipped ${res.skipped}`);
      qc.invalidateQueries({ queryKey: ["section-cards"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bulk generate</CardTitle>
        <CardDescription>Generates a card per active student in the section, idempotent on re-run.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <Label>Exam</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={examId ?? ""}
            onChange={(e) => setExamId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Select…</option>
            {exams.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>Class</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={classId ?? ""}
            onChange={(e) => {
              setClassId(e.target.value ? Number(e.target.value) : null);
              setSectionId(null);
            }}
          >
            <option value="">Select…</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>Section</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={sectionId ?? ""}
            onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : null)}
            disabled={classId === null}
          >
            <option value="">Select…</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>Template</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={templateId ?? ""}
            onChange={(e) => setTemplateId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Default</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div className="col-span-2 flex items-center gap-2">
          <input
            id="rc-publish"
            type="checkbox"
            checked={publish}
            onChange={(e) => setPublish(e.target.checked)}
          />
          <Label htmlFor="rc-publish">Publish on generate (parents see it immediately)</Label>
        </div>
        <div className="col-span-2">
          <Button
            onClick={() => run.mutate()}
            disabled={!examId || !sectionId || run.isPending}
          >
            <FileText className="mr-1 h-4 w-4" />
            Generate
          </Button>
          {flash && <span className="ml-3 text-sm text-teal-dark">{flash}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

// ---- Cards listing -------------------------------------------------------

function CardsPanel() {
  const qc = useQueryClient();
  const { data: exams = [] } = useQuery({ queryKey: ["exams"], queryFn: listExams });
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const [examId, setExamId] = useState<number | null>(null);
  const [classId, setClassId] = useState<number | null>(null);
  const { data: sections = [] } = useQuery({
    queryKey: ["sections", classId],
    queryFn: () => (classId ? listSections(classId) : Promise.resolve([])),
    enabled: classId !== null,
  });
  const [sectionId, setSectionId] = useState<number | null>(null);

  const { data: cards = [] } = useQuery({
    queryKey: ["section-cards", examId, sectionId],
    queryFn: () => listSectionCards(examId!, sectionId!),
    enabled: examId !== null && sectionId !== null,
  });

  const publish = useMutation({
    mutationFn: () => publishSection(examId!, sectionId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["section-cards", examId, sectionId] }),
  });

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "https://api.campus.jaikalki.in";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick exam + section</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <div>
            <Label>Exam</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={examId ?? ""}
              onChange={(e) => setExamId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select…</option>
              {exams.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Class</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={classId ?? ""}
              onChange={(e) => {
                setClassId(e.target.value ? Number(e.target.value) : null);
                setSectionId(null);
              }}
            >
              <option value="">Select…</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Section</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={sectionId ?? ""}
              onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : null)}
              disabled={classId === null}
            >
              <option value="">Select…</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {examId && sectionId && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Generated cards</CardTitle>
              <CardDescription>{cards.length} cards in this section</CardDescription>
            </div>
            <Button onClick={() => publish.mutate()} disabled={cards.length === 0 || publish.isPending}>
              <Send className="mr-1 h-4 w-4" />
              Publish all
            </Button>
          </CardHeader>
          <CardContent>
            {cards.length === 0 ? (
              <p className="text-sm text-muted-foreground">No cards generated yet.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="py-2">Student</th>
                    <th>%</th>
                    <th>Grade</th>
                    <th>Rank</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {cards.map((rc) => (
                    <tr key={rc.id} className="border-t border-saffron-pale">
                      <td className="py-2">{rc.snapshot.student?.full_name ?? `Student ${rc.student_id}`}</td>
                      <td>{rc.percentage ?? "-"}</td>
                      <td>
                        <span className="inline-flex items-center gap-1">
                          <Award className="h-3 w-3 text-saffron-dark" />
                          {rc.overall_grade ?? "-"}
                        </span>
                      </td>
                      <td>{rc.rank_in_section ?? "-"}</td>
                      <td>
                        <span className={cn("rounded px-2 py-0.5 text-xs font-medium", STATUS_TONE[rc.status])}>
                          {rc.status}
                        </span>
                      </td>
                      <td className="text-right">
                        <a
                          className="inline-flex items-center gap-1 text-teal-dark hover:underline"
                          href={`${apiBase}${pdfUrl(rc.id)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Download className="h-3 w-3" />
                          PDF
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
