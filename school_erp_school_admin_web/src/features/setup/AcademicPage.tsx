import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  activateAcademicYear,
  addTerm,
  createAcademicYear,
  createHoliday,
  deleteHoliday,
  listAcademicYears,
  listHolidays,
  type AcademicYear,
  type Holiday,
} from "./api";

export function AcademicPage() {
  const qc = useQueryClient();
  const years = useQuery({ queryKey: ["academic-years"], queryFn: listAcademicYears });
  const holidays = useQuery({ queryKey: ["holidays"], queryFn: () => listHolidays() });

  const createYear = useMutation({
    mutationFn: createAcademicYear,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-years"] }),
  });
  const activateYear = useMutation({
    mutationFn: activateAcademicYear,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["academic-years"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  const newTerm = useMutation({
    mutationFn: ({ year_id, payload }: { year_id: number; payload: any }) => addTerm(year_id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-years"] }),
  });
  const newHoliday = useMutation({
    mutationFn: createHoliday,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holidays"] }),
  });
  const removeHoliday = useMutation({
    mutationFn: deleteHoliday,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holidays"] }),
  });

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 4 · Academic</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Academic year, terms &amp; holidays</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Mark a year active. Attendance, exams, and report cards key off it.
        </p>
      </header>

      <YearForm onCreate={(payload) => createYear.mutate(payload)} pending={createYear.isPending} />

      <YearList
        years={years.data ?? []}
        loading={years.isLoading}
        onActivate={(id) => activateYear.mutate(id)}
        onAddTerm={(year_id, payload) => newTerm.mutate({ year_id, payload })}
      />

      <HolidayList
        holidays={holidays.data ?? []}
        loading={holidays.isLoading}
        onCreate={(payload) => newHoliday.mutate(payload)}
        onDelete={(id) => removeHoliday.mutate(id)}
      />
    </div>
  );
}

function YearForm({
  onCreate,
  pending,
}: {
  onCreate: (p: { code: string; name: string; start_date: string; end_date: string; is_active: boolean }) => void;
  pending: boolean;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [active, setActive] = useState(false);
  return (
    <Card>
      <CardHeader>
        <CardTitle>New academic year</CardTitle>
        <CardDescription>You can have many; only one is active at a time.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid grid-cols-2 gap-4 lg:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            onCreate({ code, name, start_date: start, end_date: end, is_active: active });
            setCode(""); setName(""); setStart(""); setEnd(""); setActive(false);
          }}
        >
          <FieldText label="Code" value={code} onChange={setCode} placeholder="2025-26" required />
          <FieldText label="Name" value={name} onChange={setName} placeholder="Academic Year 2025-26" required />
          <FieldDate label="Start" value={start} onChange={setStart} required />
          <FieldDate label="End" value={end} onChange={setEnd} required />
          <div className="flex items-end gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
                className="h-4 w-4 accent-saffron"
              />
              Mark active
            </label>
          </div>
          <div className="col-span-2 lg:col-span-5 flex justify-end">
            <Button type="submit" disabled={pending}>
              <Plus className="h-4 w-4" />
              {pending ? "Adding…" : "Add year"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function YearList({
  years,
  loading,
  onActivate,
  onAddTerm,
}: {
  years: AcademicYear[];
  loading: boolean;
  onActivate: (id: number) => void;
  onAddTerm: (year_id: number, payload: { name: string; start_date: string; end_date: string }) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Years &amp; terms</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !years.length ? (
          <p className="text-sm text-muted-foreground">No years yet.</p>
        ) : (
          <ul className="space-y-3">
            {years.map((y) => (
              <li key={y.id} className="rounded-lg border border-saffron-pale bg-warm-white p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="flex items-center gap-2 font-display text-lg text-indigo-dark">
                      {y.name}
                      {y.is_active && (
                        <span className="rounded-full bg-teal-pale px-2 py-0.5 text-[11px] font-medium text-teal-dark">
                          active
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      <span className="font-mono">{y.code}</span> · {y.start_date} → {y.end_date}
                    </p>
                  </div>
                  {!y.is_active && (
                    <Button variant="outline" size="sm" onClick={() => onActivate(y.id)}>
                      <CheckCircle2 className="h-4 w-4" />
                      Activate
                    </Button>
                  )}
                </div>
                <div className="mt-3 grid gap-2 lg:grid-cols-2">
                  {y.terms.map((t) => (
                    <div key={t.id} className="rounded-md border border-saffron-pale px-3 py-2 text-sm">
                      <p className="font-medium text-indigo-dark">{t.name}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {t.start_date} → {t.end_date}
                      </p>
                    </div>
                  ))}
                  <TermInline year_id={y.id} onSubmit={onAddTerm} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function TermInline({
  year_id,
  onSubmit,
}: {
  year_id: number;
  onSubmit: (year_id: number, payload: { name: string; start_date: string; end_date: string }) => void;
}) {
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(year_id, { name, start_date: start, end_date: end });
        setName(""); setStart(""); setEnd("");
      }}
      className="flex flex-col gap-2 rounded-md border border-dashed border-saffron-pale p-2 text-sm"
    >
      <p className="text-xs uppercase tracking-wider text-saffron-dark">+ Add term</p>
      <div className="flex flex-wrap gap-2">
        <Input placeholder="Term name" value={name} onChange={(e) => setName(e.target.value)} className="min-w-[140px] flex-1" />
        <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="w-44" />
        <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="w-44" />
        <Button size="sm" type="submit" disabled={!name || !start || !end}>
          Add
        </Button>
      </div>
    </form>
  );
}

function HolidayList({
  holidays,
  loading,
  onCreate,
  onDelete,
}: {
  holidays: Holiday[];
  loading: boolean;
  onCreate: (payload: any) => void;
  onDelete: (id: number) => void;
}) {
  const [date, setDate] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Holiday["kind"]>("public");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Holidays</CardTitle>
        <CardDescription>Public, school-specific, or vacation periods.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid grid-cols-2 gap-3 lg:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            onCreate({ date, name, kind });
            setDate(""); setName("");
          }}
        >
          <FieldDate label="Date" value={date} onChange={setDate} required />
          <FieldText label="Name" value={name} onChange={setName} required />
          <div className="space-y-1.5">
            <Label>Kind</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={kind}
              onChange={(e) => setKind(e.target.value as Holiday["kind"])}
            >
              <option value="public">Public</option>
              <option value="school">School-specific</option>
              <option value="optional">Optional</option>
              <option value="vacation">Vacation</option>
            </select>
          </div>
          <div className="col-span-2 flex items-end justify-end lg:col-span-2">
            <Button type="submit" disabled={!date || !name}>
              <Plus className="h-4 w-4" />
              Add holiday
            </Button>
          </div>
        </form>

        <hr className="my-4 border-saffron-pale" />

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !holidays.length ? (
          <p className="text-sm text-muted-foreground">No holidays added yet.</p>
        ) : (
          <ul className="divide-y divide-saffron-pale">
            {holidays.map((h) => (
              <li key={h.id} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-indigo-dark">{h.name}</p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-mono">{h.date}</span> · {h.kind}
                  </p>
                </div>
                <Button variant="ghost" size="icon" onClick={() => onDelete(h.id)}>
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function FieldText({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-destructive"> *</span>}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function FieldDate({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-destructive"> *</span>}</Label>
      <Input type="date" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
