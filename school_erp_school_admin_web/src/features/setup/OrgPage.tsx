import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  createClass,
  createDepartment,
  createSection,
  createSubject,
  deleteClass,
  deleteDepartment,
  deleteSection,
  deleteSubject,
  listClasses,
  listDepartments,
  listSections,
  listSubjects,
  type ClassDef,
  type Department,
  type Section,
  type Subject,
} from "./api";

const STAGES = [
  { code: "pre_primary", label: "Pre-Primary" },
  { code: "primary", label: "Primary" },
  { code: "middle", label: "Middle" },
  { code: "secondary", label: "Secondary" },
  { code: "senior_secondary", label: "Senior Secondary" },
] as const;

const TABS = ["Departments", "Classes", "Sections", "Subjects"] as const;
type Tab = (typeof TABS)[number];

export function OrgPage() {
  const [tab, setTab] = useState<Tab>("Departments");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 4 · Organisation</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Departments, classes, sections, subjects</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          The skeleton your students, teachers, and timetables hang off.
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

      {tab === "Departments" && <DepartmentsPanel />}
      {tab === "Classes" && <ClassesPanel />}
      {tab === "Sections" && <SectionsPanel />}
      {tab === "Subjects" && <SubjectsPanel />}
    </div>
  );
}

// ---- Departments -----------------------------------------------------------

function DepartmentsPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["departments"], queryFn: listDepartments });
  const create = useMutation({
    mutationFn: createDepartment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["departments"] }),
  });
  const remove = useMutation({
    mutationFn: deleteDepartment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["departments"] }),
  });

  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <ListCard
        title="Departments"
        items={list.data ?? []}
        loading={list.isLoading}
        renderRow={(d: Department) => (
          <RowShell key={d.id} onDelete={() => remove.mutate(d.id)}>
            <span className="font-medium text-indigo-dark">{d.name}</span>
            <span className="text-xs font-mono text-saffron-dark">{d.code ?? ""}</span>
          </RowShell>
        )}
      />
      <Card>
        <CardHeader>
          <CardTitle>Add department</CardTitle>
          <CardDescription>HOD assignment lands when teachers are onboarded (Phase 7).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <FieldText label="Name" value={name} onChange={setName} />
          <FieldText label="Code" value={code} onChange={setCode} />
          <Button
            disabled={!name || create.isPending}
            onClick={() => create.mutate({ name, code: code || undefined }, { onSuccess: () => { setName(""); setCode(""); } })}
          >
            <Plus className="h-4 w-4" />
            Add
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Classes ---------------------------------------------------------------

function ClassesPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });
  const create = useMutation({
    mutationFn: createClass,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classes"] }),
  });
  const remove = useMutation({
    mutationFn: deleteClass,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["classes"] }),
  });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [stage, setStage] = useState<ClassDef["stage"]>("primary");
  const [sequence, setSequence] = useState(0);
  const [departmentId, setDepartmentId] = useState<number | "">("");

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <ListCard
        title="Classes"
        items={list.data ?? []}
        loading={list.isLoading}
        renderRow={(c: ClassDef) => (
          <RowShell key={c.id} onDelete={() => remove.mutate(c.id)}>
            <span className="font-medium text-indigo-dark">{c.name}</span>
            <span className="text-xs uppercase tracking-wider text-saffron-dark">{c.stage.replace(/_/g, " ")}</span>
          </RowShell>
        )}
      />
      <Card>
        <CardHeader>
          <CardTitle>Add class</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FieldText label="Code (e.g. 1, LKG)" value={code} onChange={setCode} />
          <FieldText label="Display name" value={name} onChange={setName} />
          <Field label="Stage">
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={stage}
              onChange={(e) => setStage(e.target.value as ClassDef["stage"])}
            >
              {STAGES.map((s) => (
                <option key={s.code} value={s.code}>{s.label}</option>
              ))}
            </select>
          </Field>
          <FieldNum label="Order in school" value={sequence} onChange={setSequence} />
          <Field label="Department">
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">— none —</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </Field>
          <Button
            disabled={!code || !name || create.isPending}
            onClick={() =>
              create.mutate(
                {
                  code,
                  name,
                  stage,
                  sequence,
                  department_id: departmentId === "" ? null : departmentId,
                },
                {
                  onSuccess: () => {
                    setCode(""); setName(""); setSequence(0); setDepartmentId("");
                  },
                },
              )
            }
          >
            <Plus className="h-4 w-4" />
            Add class
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Sections --------------------------------------------------------------

function SectionsPanel() {
  const qc = useQueryClient();
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const list = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });
  const create = useMutation({
    mutationFn: createSection,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sections"] }),
  });
  const remove = useMutation({
    mutationFn: deleteSection,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sections"] }),
  });

  const [classId, setClassId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState(40);

  const classMap = new Map((classes.data ?? []).map((c) => [c.id, c.name]));

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <ListCard
        title="Sections"
        items={list.data ?? []}
        loading={list.isLoading}
        renderRow={(s: Section) => (
          <RowShell key={s.id} onDelete={() => remove.mutate(s.id)}>
            <span className="font-medium text-indigo-dark">
              {classMap.get(s.class_def_id) ?? "?"} · Section {s.name}
            </span>
            <span className="text-xs text-muted-foreground">capacity {s.capacity}</span>
          </RowShell>
        )}
      />
      <Card>
        <CardHeader>
          <CardTitle>Add section</CardTitle>
          <CardDescription>Section in-charge can be assigned in Phase 7 (teachers).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Field label="Class">
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={classId}
              onChange={(e) => setClassId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">— pick a class —</option>
              {(classes.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </Field>
          <FieldText label="Section letter" value={name} onChange={setName} />
          <FieldNum label="Capacity" value={capacity} onChange={setCapacity} />
          <Button
            disabled={classId === "" || !name || create.isPending}
            onClick={() =>
              create.mutate(
                { class_def_id: Number(classId), name, capacity },
                { onSuccess: () => { setName(""); setCapacity(40); } },
              )
            }
          >
            <Plus className="h-4 w-4" />
            Add section
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Subjects --------------------------------------------------------------

function SubjectsPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });
  const create = useMutation({
    mutationFn: createSubject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });
  const remove = useMutation({
    mutationFn: deleteSubject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [isCore, setIsCore] = useState(true);
  const [isLanguage, setIsLanguage] = useState(false);
  const [hasPractical, setHasPractical] = useState(false);

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <ListCard
        title="Subjects"
        items={list.data ?? []}
        loading={list.isLoading}
        renderRow={(s: Subject) => (
          <RowShell key={s.id} onDelete={() => remove.mutate(s.id)}>
            <span className="font-medium text-indigo-dark">{s.name}</span>
            <span className="flex gap-1">
              {s.is_core && <Badge>core</Badge>}
              {s.is_language && <Badge>language</Badge>}
              {s.has_practical && <Badge>practical</Badge>}
            </span>
          </RowShell>
        )}
      />
      <Card>
        <CardHeader>
          <CardTitle>Add subject</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FieldText label="Code" value={code} onChange={setCode} />
          <FieldText label="Name" value={name} onChange={setName} />
          <CheckboxRow label="Core subject" checked={isCore} onChange={setIsCore} />
          <CheckboxRow label="Language" checked={isLanguage} onChange={setIsLanguage} />
          <CheckboxRow label="Has practical" checked={hasPractical} onChange={setHasPractical} />
          <Button
            disabled={!code || !name || create.isPending}
            onClick={() =>
              create.mutate(
                { code, name, is_core: isCore, is_language: isLanguage, has_practical: hasPractical },
                { onSuccess: () => { setCode(""); setName(""); setIsLanguage(false); setHasPractical(false); } },
              )
            }
          >
            <Plus className="h-4 w-4" />
            Add subject
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- shared bits -----------------------------------------------------------

function ListCard<T>({
  title,
  items,
  loading,
  renderRow,
}: {
  title: string;
  items: T[];
  loading: boolean;
  renderRow: (item: T) => React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{items.length || 0} entries</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
        ) : !items.length ? (
          <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet — use the form on the right.</p>
        ) : (
          <ul className="divide-y divide-saffron-pale">{items.map(renderRow)}</ul>
        )}
      </CardContent>
    </Card>
  );
}

function RowShell({ children, onDelete }: { children: React.ReactNode; onDelete: () => void }) {
  return (
    <li className="flex items-center justify-between px-6 py-3 text-sm">
      <div className="flex items-center gap-3">{children}</div>
      <Button variant="ghost" size="icon" onClick={onDelete}>
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </li>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function FieldText({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <Field label={label}>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </Field>
  );
}

function FieldNum({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <Field label={label}>
      <Input type="number" value={value} onChange={(e) => onChange(Number(e.target.value) || 0)} />
    </Field>
  );
}

function CheckboxRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-input accent-saffron"
      />
      {label}
    </label>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-saffron-pale bg-saffron-pale/40 px-2 py-0.5 text-[10px] uppercase tracking-wider text-saffron-darker">
      {children}
    </span>
  );
}
