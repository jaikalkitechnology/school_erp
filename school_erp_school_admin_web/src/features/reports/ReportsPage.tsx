import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import {
  attendanceTrend,
  examAnalytics,
  fees as feesAnalytics,
  hostelSummary,
  libraryUsage,
  overview,
  studentReport,
  studentReportCsvUrl,
  transportSummary,
} from "./api";

const TABS = ["Overview", "Attendance", "Fees", "Exams", "Modules", "Students"] as const;
type Tab = (typeof TABS)[number];

const PALETTE = ["#E85D2E", "#FFB800", "#0F766E", "#1F1248", "#A855F7", "#F472B6"];

export function ReportsPage() {
  const [tab, setTab] = useState<Tab>("Overview");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 20 · Reports & analytics
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Reports</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Cross-module dashboards across attendance, fees, exams, library, transport, and
          hostel. Export student lists to CSV with one click.
        </p>
      </header>
      <nav className="flex flex-wrap gap-1 border-b border-saffron-pale">
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
      {tab === "Overview" && <OverviewPanel />}
      {tab === "Attendance" && <AttendancePanel />}
      {tab === "Fees" && <FeesPanel />}
      {tab === "Exams" && <ExamsPanel />}
      {tab === "Modules" && <ModulesPanel />}
      {tab === "Students" && <StudentsReportPanel />}
    </div>
  );
}

// ---- Overview -----------------------------------------------------------

function OverviewPanel() {
  const { data } = useQuery({ queryKey: ["analytics-overview"], queryFn: overview });
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <Tile label="Students" value={data.students} />
        <Tile label="Teachers" value={data.teachers} />
        <Tile label="Classes" value={data.classes} />
        <Tile label="Sections" value={data.sections} />
        <Tile label="Attendance today" value={`${data.attendance_today_pct}%`} tone="teal" />
        <Tile label="Collected this month" value={`₹${data.fee_collected_this_month}`} tone="teal" />
        <Tile label="Pending fees" value={`₹${data.fee_pending}`} tone="marigold" />
        <Tile label="Overdue loans" value={data.overdue_loans} tone="destructive" />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Class strength</CardTitle>
          <CardDescription>Active students per class.</CardDescription>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.by_class_strength}>
              <CartesianGrid strokeDasharray="3 3" stroke="#FFE4B8" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#E85D2E" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Attendance --------------------------------------------------------

function AttendancePanel() {
  const [days, setDays] = useState(14);
  const { data } = useQuery({
    queryKey: ["analytics-attendance", days],
    queryFn: () => attendanceTrend(days),
  });
  if (!data) return null;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Attendance trend</CardTitle>
          <CardDescription>
            Average across the window: <span className="font-medium text-indigo-dark">{data.average_pct}%</span>
          </CardDescription>
        </div>
        <select
          className="h-9 rounded border border-input bg-transparent px-2 text-sm"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          {[7, 14, 30, 60].map((d) => (
            <option key={d} value={d}>{d} days</option>
          ))}
        </select>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#FFE4B8" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} unit="%" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#0F766E"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#E85D2E" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ---- Fees ---------------------------------------------------------------

function FeesPanel() {
  const { data } = useQuery({ queryKey: ["analytics-fees"], queryFn: feesAnalytics });
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <Tile label="Billed" value={`₹${data.total_billed}`} />
        <Tile label="Collected" value={`₹${data.total_collected}`} tone="teal" />
        <Tile label="Pending" value={`₹${data.pending}`} tone="marigold" />
        <Tile label="Overdue invoices" value={data.overdue_count} tone="destructive" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By method</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.by_method} dataKey="value" nameKey="label" outerRadius={80} label>
                  {data.by_method.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>By category</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.by_category}>
                <CartesianGrid strokeDasharray="3 3" stroke="#FFE4B8" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#FFB800" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ---- Exams --------------------------------------------------------------

function ExamsPanel() {
  const { data } = useQuery({ queryKey: ["analytics-exams"], queryFn: () => examAnalytics() });
  if (!data) return null;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Per-section averages</CardTitle>
          <CardDescription>Latest exams</CardDescription>
        </CardHeader>
        <CardContent>
          {data.rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No marks recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Exam</th>
                  <th>Section</th>
                  <th>Avg %</th>
                  <th>Pass %</th>
                  <th>Students</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r, i) => (
                  <tr key={i} className="border-t border-saffron-pale">
                    <td className="py-2 font-medium text-indigo-dark">{r.exam_name}</td>
                    <td>{r.section_name ?? "—"}</td>
                    <td>{r.average_pct}%</td>
                    <td>
                      <span className={cn(
                        "rounded px-2 py-0.5 text-xs",
                        r.pass_pct >= 75 ? "bg-teal-pale text-teal-dark"
                          : r.pass_pct >= 50 ? "bg-marigold-pale text-marigold-dark"
                          : "bg-destructive/15 text-destructive",
                      )}>
                        {r.pass_pct}%
                      </span>
                    </td>
                    <td>{r.student_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
      {data.grade_distribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Grade distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.grade_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#FFE4B8" />
                <XAxis dataKey="label" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#1F1248" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Modules (library + transport + hostel) ---------------------------

function ModulesPanel() {
  const { data: lib } = useQuery({ queryKey: ["analytics-library"], queryFn: libraryUsage });
  const { data: tr } = useQuery({ queryKey: ["analytics-transport"], queryFn: transportSummary });
  const { data: ho } = useQuery({ queryKey: ["analytics-hostel"], queryFn: hostelSummary });
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Library</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Tile label="Issued today" value={lib?.issued_today ?? 0} />
            <Tile label="Overdue" value={lib?.overdue ?? 0} tone="destructive" />
          </div>
          {lib?.most_loaned && lib.most_loaned.length > 0 && (
            <div className="mt-4 h-48">
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Most loaned</p>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={lib.most_loaned} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#FFE4B8" />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis dataKey="label" type="category" tick={{ fontSize: 11 }} width={120} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0F766E" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Transport</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            <Tile label="Routes" value={tr?.routes ?? 0} />
            <Tile label="Buses" value={tr?.buses ?? 0} />
            <Tile label="Drivers" value={tr?.drivers ?? 0} />
            <Tile label="Allocated" value={tr?.students_allocated ?? 0} />
            <Tile label="Active trips" value={tr?.active_trips_today ?? 0} tone="saffron" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Hostel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            <Tile label="Occupied" value={ho?.occupied ?? 0} tone="marigold" />
            <Tile label="Available" value={ho?.available_seats ?? 0} tone="teal" />
            <Tile label="Pending leaves" value={ho?.pending_leaves ?? 0} tone="saffron" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Students report --------------------------------------------------

function StudentsReportPanel() {
  const { data: classes = [] } = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const [classId, setClassId] = useState<string>("");
  const { data: sections = [] } = useQuery({
    queryKey: ["sections", classId],
    queryFn: () => (classId ? listSections(Number(classId)) : Promise.resolve([])),
    enabled: !!classId,
  });
  const [sectionId, setSectionId] = useState<string>("");
  const params = useMemo(
    () => ({
      class_def_id: classId ? Number(classId) : undefined,
      section_id: sectionId ? Number(sectionId) : undefined,
      only_active: true,
    }),
    [classId, sectionId],
  );
  const { data: rows = [] } = useQuery({
    queryKey: ["analytics-student-report", params],
    queryFn: () => studentReport(params),
  });
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "https://api.campus.jaikalki.in";
  const csvHref = `${apiBase}${studentReportCsvUrl(params)}`;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Student directory</CardTitle>
          <CardDescription>{rows.length} students</CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={classId}
            onChange={(e) => {
              setClassId(e.target.value);
              setSectionId("");
            }}
          >
            <option value="">All classes</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value)}
            disabled={!classId}
          >
            <option value="">All sections</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <a href={csvHref} target="_blank" rel="noopener noreferrer">
            <Button size="sm" variant="outline">
              <Download className="mr-1 h-4 w-4" />
              CSV
            </Button>
          </a>
        </div>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="py-2">Adm #</th>
              <th>Name</th>
              <th>Class</th>
              <th>Section</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.student_id} className="border-t border-saffron-pale">
                <td className="py-2">{r.admission_number}</td>
                <td className="font-medium text-indigo-dark">{r.full_name}</td>
                <td>{r.class_label ?? "—"}</td>
                <td>{r.section_name ?? "—"}</td>
                <td>{r.parent_phone ?? "—"}</td>
                <td>{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "marigold" | "saffron" | "teal" | "destructive";
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 font-display text-2xl",
            tone === "marigold" && "text-marigold-dark",
            tone === "saffron" && "text-saffron-darker",
            tone === "teal" && "text-teal-dark",
            tone === "destructive" && "text-destructive",
            !tone && "text-indigo-dark",
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
