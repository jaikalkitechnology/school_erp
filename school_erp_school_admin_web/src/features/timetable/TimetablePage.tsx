import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CalendarClock, Check, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections, listSubjects } from "@/features/setup/api";
import { listTeachers } from "@/features/teachers/api";
import {
  assignSub,
  cancelSub,
  completeSub,
  listSubsForDate,
  saveSection,
  sectionTimetable,
  suggestSubs,
  type Cell,
} from "./api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

const TABS = ["Section grid", "Substitutions"] as const;
type Tab = (typeof TABS)[number];

export function TimetablePage() {
  const [tab, setTab] = useState<Tab>("Section grid");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 13 · Timetable</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Time table &amp; substitution</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Build the weekly grid per section; conflicts are caught before save. Suggest a substitute
          when a teacher is out.
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
      {tab === "Section grid" && <SectionGridPanel />}
      {tab === "Substitutions" && <SubstitutionsPanel />}
    </div>
  );
}

// ---- Section grid ---------------------------------------------------------

function SectionGridPanel() {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });
  const teachers = useQuery({ queryKey: ["teachers", "for-tt"], queryFn: () => listTeachers({ limit: 200 }) });

  const [sectionId, setSectionId] = useState<number | "">("");
  const grid = useQuery({
    queryKey: ["section-tt", sectionId],
    queryFn: () => sectionTimetable(Number(sectionId)),
    enabled: sectionId !== "",
  });

  const [cells, setCells] = useState<Map<string, Cell>>(new Map());
  const [conflicts, setConflicts] = useState<{ day: number; period: number; other: number }[]>([]);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    if (!grid.data) return;
    const m = new Map<string, Cell>();
    grid.data.cells.forEach((c) => m.set(`${c.day_of_week}-${c.period_number}`, c));
    setCells(m);
    setConflicts([]);
  }, [grid.data]);

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );

  const setCell = (day: number, period: number, patch: Partial<Cell>) => {
    setCells((m) => {
      const next = new Map(m);
      const key = `${day}-${period}`;
      const existing = next.get(key) ?? {
        day_of_week: day, period_number: period,
        subject_id: null, teacher_user_id: null, room: null,
      };
      next.set(key, { ...existing, ...patch });
      return next;
    });
    setSavedFlash(false);
  };

  const save = useMutation({
    mutationFn: () =>
      saveSection(Number(sectionId), Array.from(cells.values())),
    onSuccess: (res) => {
      if (res.conflicts.length) {
        setConflicts(res.conflicts.map((c) => ({
          day: c.day_of_week, period: c.period_number, other: c.other_section_id,
        })));
        setSavedFlash(false);
      } else {
        setConflicts([]);
        setSavedFlash(true);
        qc.invalidateQueries({ queryKey: ["section-tt", sectionId] });
      }
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Pick a section</CardTitle></CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>

      {sectionId !== "" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Weekly grid</CardTitle>
              <CardDescription>
                Each cell takes a subject + teacher (+ optional room). Save runs a tenant-wide
                conflict check.
              </CardDescription>
            </div>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              <Save className="h-4 w-4" />
              {save.isPending ? "Saving…" : "Save grid"}
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {savedFlash && (
              <div className="border-b border-teal/30 bg-teal-pale px-6 py-2 text-sm text-teal-dark">
                Grid saved.
              </div>
            )}
            {conflicts.length > 0 && (
              <div className="border-b border-destructive/30 bg-destructive/10 px-6 py-3 text-sm text-destructive">
                <p className="flex items-center gap-2 font-medium">
                  <AlertTriangle className="h-4 w-4" />
                  {conflicts.length} conflict{conflicts.length === 1 ? "" : "s"} blocked the save
                </p>
                <ul className="mt-1 list-disc pl-5 text-xs">
                  {conflicts.map((c, i) => (
                    <li key={i}>
                      {DAYS[c.day]} · Period {c.period}: teacher already booked in section #{c.other}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-4 py-2"></th>
                    {DAYS.map((d, i) => (
                      <th key={i} className="px-4 py-2">{d}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PERIODS.map((p) => (
                    <tr key={p} className="border-b last:border-b-0">
                      <td className="px-4 py-2 font-mono text-xs text-saffron-dark align-top">P{p}</td>
                      {DAYS.map((_d, day) => {
                        const cell = cells.get(`${day}-${p}`);
                        const inConflict = conflicts.some((c) => c.day === day && c.period === p);
                        return (
                          <td
                            key={day}
                            className={cn(
                              "min-w-[180px] border-l border-saffron-pale px-2 py-2 align-top",
                              inConflict && "bg-destructive/10",
                            )}
                          >
                            <select
                              className="h-9 w-full rounded-md border border-input bg-background px-2 text-xs"
                              value={cell?.subject_id ?? ""}
                              onChange={(e) =>
                                setCell(day, p, { subject_id: e.target.value ? Number(e.target.value) : null })
                              }
                            >
                              <option value="">— subject —</option>
                              {(subjects.data ?? []).map((s) => (
                                <option key={s.id} value={s.id}>{s.code}</option>
                              ))}
                            </select>
                            <select
                              className="mt-1 h-9 w-full rounded-md border border-input bg-background px-2 text-xs"
                              value={cell?.teacher_user_id ?? ""}
                              onChange={(e) =>
                                setCell(day, p, { teacher_user_id: e.target.value ? Number(e.target.value) : null })
                              }
                            >
                              <option value="">— teacher —</option>
                              {(teachers.data?.items ?? []).map((t) => (
                                <option key={t.user_id} value={t.user_id}>{t.full_name}</option>
                              ))}
                            </select>
                            <Input
                              placeholder="Room"
                              value={cell?.room ?? ""}
                              onChange={(e) => setCell(day, p, { room: e.target.value || null })}
                              className="mt-1 h-8 text-xs"
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Substitutions --------------------------------------------------------

function SubstitutionsPanel() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [absentTeacherUserId, setAbsentTeacherUserId] = useState<number | "">("");
  const teachers = useQuery({ queryKey: ["teachers", "for-tt"], queryFn: () => listTeachers({ limit: 200 }) });
  const subjects = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const teacherMap = useMemo(
    () => new Map((teachers.data?.items ?? []).map((t) => [t.user_id, t])),
    [teachers.data],
  );
  const subjectMap = useMemo(
    () => new Map((subjects.data ?? []).map((s) => [s.id, s])),
    [subjects.data],
  );

  const suggestion = useQuery({
    queryKey: ["sub-suggest", date, absentTeacherUserId],
    queryFn: () => suggestSubs(date, Number(absentTeacherUserId)),
    enabled: absentTeacherUserId !== "",
  });
  const subs = useQuery({ queryKey: ["subs-for-date", date], queryFn: () => listSubsForDate(date) });

  const assign = useMutation({
    mutationFn: (payload: { section_id: number; period_number: number; substitute_teacher_user_id: number }) =>
      assignSub({ date, ...payload, reason: `Cover for user #${absentTeacherUserId}` }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subs-for-date", date] });
    },
  });
  const complete = useMutation({
    mutationFn: completeSub,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subs-for-date", date] }),
  });
  const cancel = useMutation({
    mutationFn: cancelSub,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subs-for-date", date] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5" />
            Pick date + absent teacher
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Date</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Absent teacher</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={absentTeacherUserId}
              onChange={(e) =>
                setAbsentTeacherUserId(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">— pick a teacher —</option>
              {(teachers.data?.items ?? []).map((t) => (
                <option key={t.user_id} value={t.user_id}>{t.full_name}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {suggestion.data && (
        <Card>
          <CardHeader>
            <CardTitle>Suggestions</CardTitle>
            <CardDescription>
              Free + qualified teachers per period the absent teacher would normally take.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {!suggestion.data.entries.length ? (
              <p className="px-6 py-4 text-sm text-muted-foreground">
                No periods scheduled for this teacher on that weekday.
              </p>
            ) : (
              <ul className="divide-y divide-saffron-pale">
                {suggestion.data.entries.map((e) => (
                  <li key={`${e.section_id}-${e.period_number}`} className="px-6 py-3 text-sm">
                    <p className="font-medium text-indigo-dark">
                      Period {e.period_number} · Section #{e.section_id}
                      {e.subject_id && ` · ${subjectMap.get(e.subject_id)?.code ?? ""}`}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {e.suggested_substitutes.length === 0 ? (
                        <span className="text-xs text-muted-foreground">No free qualified teacher.</span>
                      ) : (
                        e.suggested_substitutes.map((uid) => (
                          <Button
                            key={uid}
                            size="sm"
                            variant="outline"
                            disabled={assign.isPending}
                            onClick={() =>
                              assign.mutate({
                                section_id: e.section_id,
                                period_number: e.period_number,
                                substitute_teacher_user_id: uid,
                              })
                            }
                          >
                            Assign {teacherMap.get(uid)?.full_name ?? `#${uid}`}
                          </Button>
                        ))
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Substitutions for {date}</CardTitle></CardHeader>
        <CardContent className="p-0">
          {!subs.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No substitutions scheduled.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Section</th>
                  <th className="px-4 py-3">Period</th>
                  <th className="px-4 py-3">Substitute</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {subs.data.map((s) => (
                  <tr key={s.id} className="border-b last:border-b-0">
                    <td className="px-6 py-2">
                      Section #{s.section_id}
                      {s.subject_id && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({subjectMap.get(s.subject_id)?.code ?? ""})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 font-mono">P{s.period_number}</td>
                    <td className="px-4 py-2">
                      {s.substitute_teacher_user_id
                        ? teacherMap.get(s.substitute_teacher_user_id)?.full_name ?? `#${s.substitute_teacher_user_id}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2 capitalize">{s.status}</td>
                    <td className="px-6 py-2 text-right">
                      {s.status === "assigned" && (
                        <>
                          <Button size="sm" variant="ghost" onClick={() => complete.mutate(s.id)}>
                            <Check className="h-3.5 w-3.5" /> Done
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => cancel.mutate(s.id)}>
                            <X className="h-3.5 w-3.5" /> Cancel
                          </Button>
                        </>
                      )}
                    </td>
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
