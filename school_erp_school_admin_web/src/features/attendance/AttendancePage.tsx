import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, ClipboardList, Save, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import {
  defaulterList,
  markRoll,
  sectionMonthly,
  sectionRoll,
  type AttendanceStatus,
  type RollEntry,
} from "./api";

const STATUS_TONE: Record<AttendanceStatus, string> = {
  present: "bg-teal-pale text-teal-dark border-teal/40",
  absent: "bg-saffron-pale text-saffron-darker border-saffron",
  late: "bg-marigold-pale text-marigold-dark border-marigold/60",
  leave: "bg-muted text-muted-foreground border-border",
  half_day: "bg-marigold-pale/60 text-marigold-dark border-marigold/40",
};

const STATUS_LABEL: Record<AttendanceStatus, string> = {
  present: "P",
  absent: "A",
  late: "L",
  leave: "Lv",
  half_day: "½",
};

const TABS = ["Roll-call", "Monthly", "Defaulters"] as const;
type Tab = (typeof TABS)[number];

export function AttendancePage() {
  const [tab, setTab] = useState<Tab>("Roll-call");

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 9 · Attendance</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Roll-call &amp; reports</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Mark daily attendance, review the monthly summary, and surface low-attendance defaulters.
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

      {tab === "Roll-call" && <RollCallPanel />}
      {tab === "Monthly" && <MonthlyPanel />}
      {tab === "Defaulters" && <DefaultersPanel />}
    </div>
  );
}

// ---- Roll-call ------------------------------------------------------------

function RollCallPanel() {
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [sectionId, setSectionId] = useState<number | "">("");
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const roll = useQuery({
    queryKey: ["roll", sectionId, date],
    queryFn: () => sectionRoll(Number(sectionId), date),
    enabled: sectionId !== "",
  });

  const [draft, setDraft] = useState<Record<number, AttendanceStatus>>({});
  const [remarks, setRemarks] = useState<Record<number, string>>({});
  const qc = useQueryClient();

  useEffect(() => {
    if (roll.data) {
      const next: Record<number, AttendanceStatus> = {};
      const r: Record<number, string> = {};
      for (const s of roll.data.students) {
        next[s.student_id] = s.status;
        r[s.student_id] = s.remarks ?? "";
      }
      setDraft(next);
      setRemarks(r);
    }
  }, [roll.data]);

  const save = useMutation({
    mutationFn: () =>
      markRoll({
        section_id: Number(sectionId),
        date,
        default_status: "present",
        entries: Object.entries(draft).map(([sid, status]) => ({
          student_id: Number(sid),
          status,
          remarks: remarks[Number(sid)] || undefined,
        })),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roll", sectionId, date] }),
  });

  const markAllPresent = () => {
    const next: Record<number, AttendanceStatus> = {};
    (roll.data?.students ?? []).forEach((s) => { next[s.student_id] = "present"; });
    setDraft(next);
  };

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = { present: 0, absent: 0, late: 0, leave: 0, half_day: 0, unmarked: 0 };
    (roll.data?.students ?? []).forEach((s) => {
      const v = draft[s.student_id] ?? s.status;
      c[v] = (c[v] ?? 0) + 1;
    });
    return c;
  }, [draft, roll.data]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick section + date</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="space-y-1.5">
              <Label>Section</Label>
              <select
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={sectionId}
                onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">— pick a section —</option>
                {(sections.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {classMap.get(s.class_def_id) ?? "?"} · Section {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Date</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="flex items-end">
              <Button
                disabled={!roll.data?.students.length}
                onClick={markAllPresent}
              >
                <CheckCheck className="h-4 w-4" />
                Mark all present
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {sectionId !== "" && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Roster</CardTitle>
                <CardDescription>
                  {Object.entries(counts).map(([k, v]) => `${k}:${v}`).join(" · ")}
                </CardDescription>
              </div>
              <Button onClick={() => save.mutate()} disabled={save.isPending}>
                <Save className="h-4 w-4" />
                {save.isPending ? "Saving…" : "Save attendance"}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {roll.isLoading ? (
                <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
              ) : !roll.data?.students.length ? (
                <p className="px-6 py-4 text-sm text-muted-foreground">No students in this section.</p>
              ) : (
                <ul className="divide-y divide-saffron-pale">
                  {roll.data.students.map((s) => (
                    <RollRow
                      key={s.student_id}
                      student={s}
                      currentStatus={draft[s.student_id] ?? s.status}
                      remarks={remarks[s.student_id] ?? ""}
                      onChangeStatus={(v) => setDraft((d) => ({ ...d, [s.student_id]: v }))}
                      onChangeRemarks={(v) => setRemarks((r) => ({ ...r, [s.student_id]: v }))}
                    />
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

const STATUSES: AttendanceStatus[] = ["present", "absent", "late", "leave", "half_day"];

function RollRow({
  student,
  currentStatus,
  remarks,
  onChangeStatus,
  onChangeRemarks,
}: {
  student: RollEntry;
  currentStatus: AttendanceStatus;
  remarks: string;
  onChangeStatus: (v: AttendanceStatus) => void;
  onChangeRemarks: (v: string) => void;
}) {
  return (
    <li className="grid grid-cols-[1fr_auto_220px] items-center gap-3 px-6 py-2 text-sm">
      <div>
        <p className="font-medium text-indigo-dark">{student.full_name}</p>
        <p className="text-xs font-mono text-muted-foreground">
          {student.admission_number}{student.roll_no ? ` · #${student.roll_no}` : ""}
        </p>
      </div>
      <div className="flex gap-1">
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChangeStatus(s)}
            className={cn(
              "h-9 w-9 rounded-md border text-sm font-semibold transition-colors",
              currentStatus === s
                ? STATUS_TONE[s]
                : "border-border text-muted-foreground hover:border-saffron-light",
            )}
            title={s.replace("_", " ")}
          >
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>
      <Input
        value={remarks}
        onChange={(e) => onChangeRemarks(e.target.value)}
        placeholder="Optional remarks"
        className="h-9"
      />
    </li>
  );
}

// ---- Monthly --------------------------------------------------------------

function MonthlyPanel() {
  const now = new Date();
  const [sectionId, setSectionId] = useState<number | "">("");
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const report = useQuery({
    queryKey: ["monthly", sectionId, year, month],
    queryFn: () => sectionMonthly(Number(sectionId), year, month),
    enabled: sectionId !== "",
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5" />
            Monthly summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="space-y-1.5">
              <Label>Section</Label>
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
            </div>
            <div className="space-y-1.5">
              <Label>Year</Label>
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value) || now.getFullYear())} />
            </div>
            <div className="space-y-1.5">
              <Label>Month</Label>
              <Input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value) || 1)} />
            </div>
          </div>
        </CardContent>
      </Card>

      {report.isLoading && sectionId !== "" ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : report.data ? (
        <Card>
          <CardHeader>
            <CardTitle>Working days: {report.data.working_days}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Student</th>
                  <th className="px-4 py-3">P / A / L / Lv / ½</th>
                  <th className="px-4 py-3 text-right">%</th>
                </tr>
              </thead>
              <tbody>
                {report.data.students.map((s) => (
                  <tr key={s.student_id} className="border-b last:border-b-0">
                    <td className="px-6 py-2">
                      <p className="font-medium text-indigo-dark">{s.full_name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{s.admission_number}</p>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {s.present} / {s.absent} / {s.late} / {s.leave} / {s.half_day}
                    </td>
                    <td className={cn(
                      "px-4 py-2 text-right font-mono",
                      s.attendance_pct < 75 ? "text-destructive" : "text-indigo-dark",
                    )}>
                      {s.attendance_pct}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

// ---- Defaulters -----------------------------------------------------------

function DefaultersPanel() {
  const [threshold, setThreshold] = useState(75);
  const [sectionId, setSectionId] = useState<number | "">("");
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const list = useQuery({
    queryKey: ["defaulters", threshold, sectionId, start, end],
    queryFn: () =>
      defaulterList({
        threshold_pct: threshold,
        section_id: sectionId === "" ? undefined : Number(sectionId),
        start: start || undefined,
        end: end || undefined,
      }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5" />
            Defaulter filter
          </CardTitle>
          <CardDescription>Students below the threshold % over the chosen window.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-4">
            <div className="space-y-1.5">
              <Label>Threshold %</Label>
              <Input type="number" min={0} max={100} value={threshold} onChange={(e) => setThreshold(Math.max(0, Math.min(100, Number(e.target.value) || 0)))} />
            </div>
            <div className="space-y-1.5">
              <Label>Section</Label>
              <select
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={sectionId}
                onChange={(e) => setSectionId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">All sections</option>
                {(sections.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>Section #{s.id} (class {s.class_def_id})</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>From</Label>
              <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>To</Label>
              <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Defaulters ({list.data?.length ?? "—"})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : !list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nobody under the threshold for this window.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Student</th>
                  <th className="px-4 py-3">Days marked</th>
                  <th className="px-4 py-3">Present</th>
                  <th className="px-4 py-3 text-right">%</th>
                </tr>
              </thead>
              <tbody>
                {list.data.map((d) => (
                  <tr key={d.student_id} className="border-b last:border-b-0">
                    <td className="px-6 py-2">
                      <p className="font-medium text-indigo-dark">{d.full_name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{d.admission_number}</p>
                    </td>
                    <td className="px-4 py-2 font-mono">{d.total_days}</td>
                    <td className="px-4 py-2 font-mono">{d.present_days}</td>
                    <td className="px-4 py-2 text-right font-mono text-destructive">{d.attendance_pct}%</td>
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
