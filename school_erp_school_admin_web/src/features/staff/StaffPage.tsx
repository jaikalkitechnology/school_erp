import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, Check, ClipboardList, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import {
  decideStaffLeave,
  getStaffRoll,
  listStaffLeaves,
  submitStaffRoll,
  type StaffAttendanceStatus,
  type StaffLeave,
  type StaffLeaveStatus,
  type StaffRollRow,
} from "./api";

const TABS = ["Attendance", "Leave queue"] as const;
type Tab = (typeof TABS)[number];

const STATUS_TONE: Record<StaffAttendanceStatus, string> = {
  present: "bg-teal-pale text-teal-dark",
  absent: "bg-destructive/15 text-destructive",
  leave: "bg-marigold-pale text-marigold-dark",
  half_day: "bg-saffron-pale text-saffron-darker",
};

const LEAVE_TONE: Record<StaffLeaveStatus, string> = {
  pending: "bg-marigold-pale text-marigold-dark",
  approved: "bg-teal-pale text-teal-dark",
  rejected: "bg-destructive/15 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
};

export function StaffPage() {
  const [tab, setTab] = useState<Tab>("Attendance");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Staff
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">
          Staff attendance &amp; leaves
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Mark today's roll for every teacher in one screen. Approve or
          reject staff leave applications as they come in.
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
      {tab === "Attendance" && <AttendancePanel />}
      {tab === "Leave queue" && <LeavePanel />}
    </div>
  );
}

// ---- Attendance panel ----------------------------------------------------

function AttendancePanel() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const roll = useQuery({
    queryKey: ["staff-roll", date],
    queryFn: () => getStaffRoll(date),
  });
  // Local edits keyed by teacher_id. Saved on Save changes.
  const [edits, setEdits] = useState<
    Record<number, { status: StaffAttendanceStatus; remarks?: string }>
  >({});
  const [flash, setFlash] = useState<string | null>(null);

  // Reset local edits whenever a new roll loads.
  useEffect(() => setEdits({}), [date, roll.data?.date]);

  const save = useMutation({
    mutationFn: () =>
      submitStaffRoll({
        date,
        entries: Object.entries(edits).map(([id, v]) => ({
          teacher_id: Number(id),
          status: v.status,
          remarks: v.remarks,
        })),
      }),
    onSuccess: (res) => {
      setFlash(`Saved ${res.written} entries.`);
      setEdits({});
      qc.invalidateQueries({ queryKey: ["staff-roll", date] });
    },
    onError: (e: any) =>
      setFlash(`Error: ${e?.response?.data?.detail ?? "Could not save"}`),
  });

  const rows = roll.data?.rows ?? [];
  const effective = (r: StaffRollRow) => edits[r.teacher_id]?.status ?? r.status;
  const counts = useMemo(() => {
    const c = { present: 0, absent: 0, leave: 0, half_day: 0, unmarked: 0 };
    for (const r of rows) {
      const s = effective(r);
      if (!s) c.unmarked += 1;
      else (c as any)[s] += 1;
    }
    return c;
  }, [rows, edits]);

  const markAll = (status: StaffAttendanceStatus) => {
    const next: typeof edits = { ...edits };
    for (const r of rows) {
      if (effective(r) !== status) {
        next[r.teacher_id] = { status, remarks: edits[r.teacher_id]?.remarks };
      }
    }
    setEdits(next);
  };

  const setOne = (id: number, status: StaffAttendanceStatus) =>
    setEdits((e) => ({ ...e, [id]: { ...e[id], status } }));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div className="flex items-end gap-3">
            <div>
              <Label>Date</Label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-48"
              />
            </div>
            <Counts {...counts} />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => markAll("present")}>
              <Check className="mr-1 h-4 w-4" />
              All present
            </Button>
            <Button
              disabled={Object.keys(edits).length === 0 || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending
                ? "Saving…"
                : `Save ${Object.keys(edits).length} change${Object.keys(edits).length === 1 ? "" : "s"}`}
            </Button>
          </div>
        </CardHeader>
        {flash && (
          <CardContent className="pt-0">
            <p
              className={cn(
                "text-sm",
                flash.startsWith("Error")
                  ? "text-destructive"
                  : "text-teal-dark",
              )}
            >
              {flash}
            </p>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarCheck className="h-5 w-5" /> Roll-call
          </CardTitle>
          <CardDescription>
            {rows.length} active teacher{rows.length === 1 ? "" : "s"} ·
            today's date {roll.data?.date ?? "…"}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {roll.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">
              No active teachers found.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="w-12 px-6 py-3">Photo</th>
                  <th className="px-4 py-3">Teacher</th>
                  <th className="px-4 py-3">Designation</th>
                  <th className="px-4 py-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const cur = effective(r);
                  const dirty = edits[r.teacher_id] !== undefined;
                  return (
                    <tr
                      key={r.teacher_id}
                      className={cn(
                        "border-b last:border-b-0",
                        dirty && "bg-saffron-pale/20",
                      )}
                    >
                      <td className="px-6 py-2">
                        <StudentAvatar
                          photoUrl={r.photo_url}
                          name={r.full_name}
                          size={32}
                        />
                      </td>
                      <td className="px-4 py-2">
                        <p className="font-medium text-indigo-dark">{r.full_name}</p>
                        <p className="font-mono text-[10px] text-muted-foreground">
                          {r.employee_no}
                        </p>
                      </td>
                      <td className="px-4 py-2 text-xs text-muted-foreground">
                        {r.designation ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <div className="inline-flex gap-1">
                          {(
                            ["present", "absent", "leave", "half_day"] as const
                          ).map((s) => (
                            <button
                              key={s}
                              type="button"
                              title={s}
                              onClick={() => setOne(r.teacher_id, s)}
                              className={cn(
                                "rounded-md border px-2 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors",
                                cur === s
                                  ? STATUS_TONE[s]
                                  : "border-input text-muted-foreground hover:bg-saffron-pale/40",
                                cur === s ? "border-transparent" : "",
                              )}
                            >
                              {s === "half_day"
                                ? "½"
                                : s === "present"
                                  ? "P"
                                  : s === "absent"
                                    ? "A"
                                    : "L"}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Counts({
  present,
  absent,
  leave,
  half_day,
  unmarked,
}: {
  present: number;
  absent: number;
  leave: number;
  half_day: number;
  unmarked: number;
}) {
  return (
    <div className="flex gap-1">
      <Pill label="P" n={present} tone="bg-teal-pale text-teal-dark" />
      <Pill label="A" n={absent} tone="bg-destructive/15 text-destructive" />
      <Pill label="L" n={leave} tone="bg-marigold-pale text-marigold-dark" />
      <Pill label="½" n={half_day} tone="bg-saffron-pale text-saffron-darker" />
      <Pill
        label="?"
        n={unmarked}
        tone="bg-muted text-muted-foreground"
      />
    </div>
  );
}

function Pill({ label, n, tone }: { label: string; n: number; tone: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider",
        tone,
      )}
    >
      {label} {n}
    </span>
  );
}

// ---- Leave queue ---------------------------------------------------------

function LeavePanel() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<StaffLeaveStatus | "">("pending");
  const leaves = useQuery({
    queryKey: ["staff-leaves", filter],
    queryFn: () => listStaffLeaves(filter || undefined),
  });
  const [opError, setOpError] = useState<string | null>(null);

  const decide = useMutation({
    mutationFn: ({
      id,
      status,
      remarks,
    }: {
      id: number;
      status: "approved" | "rejected";
      remarks?: string;
    }) =>
      decideStaffLeave(id, {
        status,
        decision_remarks: remarks,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-leaves"] });
      setOpError(null);
    },
    onError: (e: any) =>
      setOpError(e?.response?.data?.detail ?? "Could not decide"),
  });

  const rows = leaves.data ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5" /> Leave applications
          </CardTitle>
          <CardDescription>
            {rows.length} entr{rows.length === 1 ? "y" : "ies"}
          </CardDescription>
        </div>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={filter}
          onChange={(e) =>
            setFilter(e.target.value as StaffLeaveStatus | "")
          }
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </CardHeader>
      <CardContent className="p-0">
        {leaves.isLoading ? (
          <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="px-6 py-4 text-sm text-muted-foreground">
            No leaves match.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-6 py-3">Teacher</th>
                <th className="px-4 py-3">Dates</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((l) => (
                <LeaveRow
                  key={l.id}
                  leave={l}
                  isDeciding={decide.isPending}
                  onDecide={(status, remarks) =>
                    decide.mutate({ id: l.id, status, remarks })
                  }
                />
              ))}
            </tbody>
          </table>
        )}
        {opError && (
          <p className="border-t bg-destructive/10 px-6 py-2 text-xs text-destructive">
            {opError}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function LeaveRow({
  leave,
  isDeciding,
  onDecide,
}: {
  leave: StaffLeave;
  isDeciding: boolean;
  onDecide: (status: "approved" | "rejected", remarks?: string) => void;
}) {
  const [note, setNote] = useState("");
  return (
    <tr className="border-b last:border-b-0 align-top">
      <td className="px-6 py-3">
        <p className="font-medium text-indigo-dark">{leave.full_name}</p>
        <p className="font-mono text-[10px] text-muted-foreground">
          {leave.employee_no ?? "—"}
        </p>
      </td>
      <td className="px-4 py-3 text-xs">
        <p className="font-mono text-muted-foreground">
          {leave.start_date} → {leave.end_date}
        </p>
        <p className="text-[10px] uppercase tracking-wider text-saffron-dark">
          {leave.kind}
        </p>
      </td>
      <td className="px-4 py-3 text-xs">
        <p className="whitespace-pre-wrap">{leave.reason}</p>
        {leave.decision_remarks && (
          <p className="mt-1 italic text-muted-foreground">
            Note: {leave.decision_remarks}
          </p>
        )}
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
            LEAVE_TONE[leave.status],
          )}
        >
          {leave.status}
        </span>
      </td>
      <td className="px-4 py-3">
        {leave.status === "pending" ? (
          <div className="flex flex-col items-end gap-2">
            <Input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Decision note"
              className="h-8 max-w-48 text-xs"
            />
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={isDeciding}
                onClick={() => onDecide("rejected", note || undefined)}
              >
                <X className="mr-1 h-3 w-3 text-destructive" />
                Reject
              </Button>
              <Button
                size="sm"
                disabled={isDeciding}
                onClick={() => onDecide("approved", note || undefined)}
              >
                <Check className="mr-1 h-3 w-3" />
                Approve
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-right text-[10px] text-muted-foreground">
            {leave.decided_at?.split("T")[0] ?? "—"}
          </p>
        )}
      </td>
    </tr>
  );
}
