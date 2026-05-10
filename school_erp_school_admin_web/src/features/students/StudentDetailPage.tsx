import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FileCheck2, FilePlus2, Trash2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import {
  addDocument,
  deleteDocument,
  getStudent,
  verifyDocument,
  withdrawStudent,
  type StudentStatus,
} from "./api";
import { ParentLinksPanel } from "./ParentLinksPanel";

const TABS = ["Personal", "Academic", "Family", "Documents", "History"] as const;
type Tab = (typeof TABS)[number];

export function StudentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sid = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const student = useQuery({
    queryKey: ["student", sid],
    queryFn: () => getStudent(sid),
    enabled: !Number.isNaN(sid),
  });
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );
  const sectionMap = useMemo(
    () => new Map((sections.data ?? []).map((s) => [s.id, s.name])),
    [sections.data],
  );

  const [tab, setTab] = useState<Tab>("Personal");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["student", sid] });
  const wd = useMutation({
    mutationFn: (s: StudentStatus) => withdrawStudent(sid, { status: s }),
    onSuccess: invalidate,
  });

  if (student.isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (student.isError || !student.data) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-destructive">Could not load this student.</p>
        </CardContent>
      </Card>
    );
  }

  const s = student.data;
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/students")}>
          <ArrowLeft className="h-4 w-4" />
          All students
        </Button>
        <div className="ml-auto flex gap-2">
          {s.status === "active" ? (
            <Button variant="outline" onClick={() => wd.mutate("transferred")}>
              Issue TC / Withdraw
            </Button>
          ) : null}
        </div>
      </div>

      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          {s.admission_number}
          {s.sibling_group_id && (
            <span className="ml-3 inline-flex items-center gap-1 text-teal-dark">
              <Users className="h-3 w-3" />
              Sibling group #{s.sibling_group_id}
            </span>
          )}
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">{s.full_name}</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          {[s.gender, s.date_of_birth, s.current_class_label].filter(Boolean).join(" · ")} ·{" "}
          <span className="font-medium uppercase">{s.status.replace(/_/g, " ")}</span>
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

      {tab === "Personal" && <PersonalTab s={s} />}
      {tab === "Academic" && (
        <AcademicTab
          s={s}
          className={s.class_def_id ? classMap.get(s.class_def_id) ?? "?" : "—"}
          sectionName={s.section_id ? sectionMap.get(s.section_id) ?? "?" : "—"}
        />
      )}
      {tab === "Family" && (
        <div className="space-y-4">
          <FamilyTab s={s} />
          <ParentLinksPanel studentId={s.id} />
        </div>
      )}
      {tab === "Documents" && <DocumentsTab studentId={s.id} docs={s.documents} />}
      {tab === "History" && <HistoryTab s={s} />}
    </div>
  );
}

function Pair({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-2 border-b border-saffron-pale py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-indigo-dark">{value || "—"}</dd>
    </div>
  );
}

function PersonalTab({ s }: { s: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal</CardTitle>
        <CardDescription>Demographics + medical.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Pair label="First name" value={s.first_name} />
            <Pair label="Last name" value={s.last_name} />
            <Pair label="Date of birth" value={s.date_of_birth} />
            <Pair label="Gender" value={s.gender} />
            <Pair label="Blood group" value={s.blood_group} />
            <Pair label="Aadhaar" value={s.aadhaar} />
            <Pair label="Religion" value={s.religion} />
            <Pair label="Category" value={s.category} />
          </div>
          <div>
            <Pair label="Address" value={s.address} />
            <Pair label="Phone" value={s.phone} />
            <Pair label="Email" value={s.email} />
            <Pair label="Allergies" value={s.allergies} />
            <Pair label="Medical conditions" value={s.medical_conditions} />
            <Pair label="Emergency contact" value={s.emergency_contact_name} />
            <Pair label="Emergency phone" value={s.emergency_phone} />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function AcademicTab({
  s,
  className,
  sectionName,
}: {
  s: any;
  className: string;
  sectionName: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Academic</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Pair label="Admission no." value={s.admission_number} />
            <Pair label="Roll no." value={s.roll_no} />
            <Pair label="Admission date" value={s.admission_date} />
            <Pair label="Class" value={className} />
            <Pair label="Section" value={sectionName} />
          </div>
          <div>
            <Pair label="House" value={s.house_id ? `#${s.house_id}` : "—"} />
            <Pair label="Previous school" value={s.previous_school} />
            <Pair label="Status" value={s.status} />
            <Pair label="Exit date" value={s.exit_date} />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function FamilyTab({ s }: { s: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Family</CardTitle>
        <CardDescription>
          Sibling group:{" "}
          {s.sibling_group_id ? (
            <>
              <Users className="inline h-3.5 w-3.5 text-teal-dark" />
              <span className="ml-1 text-teal-dark">{s.sibling_group_id}</span>
              {s.sibling_ids?.length > 0 && (
                <span className="ml-2 text-xs">
                  Linked siblings:{" "}
                  {s.sibling_ids.map((sid: number, i: number) => (
                    <Link key={sid} to={`/students/${sid}`} className="text-saffron-dark hover:underline">
                      #{sid}{i < s.sibling_ids.length - 1 ? ", " : ""}
                    </Link>
                  ))}
                </span>
              )}
            </>
          ) : (
            "none yet"
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Pair label="Father" value={s.father_name} />
            <Pair label="Mother" value={s.mother_name} />
            <Pair label="Guardian" value={s.guardian_name} />
          </div>
          <div>
            <Pair label="Parent phone" value={s.parent_phone} />
            <Pair label="Parent email" value={s.parent_email} />
            <Pair label="Parent occupation" value={s.parent_occupation} />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

const DOC_KINDS = [
  "birth_certificate",
  "aadhaar",
  "tc",
  "photo",
  "caste",
  "address",
] as const;

function DocumentsTab({ studentId, docs }: { studentId: number; docs: any[] }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["student", studentId] });

  const add = useMutation({
    mutationFn: (payload: { kind: string; label: string; path: string }) => addDocument(studentId, payload),
    onSuccess: invalidate,
  });
  const verify = useMutation({
    mutationFn: (did: number) => verifyDocument(studentId, did),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (did: number) => deleteDocument(studentId, did),
    onSuccess: invalidate,
  });

  const [kind, setKind] = useState<string>("birth_certificate");
  const [label, setLabel] = useState("");
  const [path, setPath] = useState("");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Add document</CardTitle>
          <CardDescription>
            Path is the relative path returned by <code className="font-mono">POST /v1/uploads</code>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-3 gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              add.mutate({ kind, label, path }, { onSuccess: () => { setLabel(""); setPath(""); } });
            }}
          >
            <div className="space-y-1.5">
              <Label>Kind</Label>
              <select
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                {DOC_KINDS.map((k) => (
                  <option key={k} value={k}>{k.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Label</Label>
              <Input value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Path</Label>
              <Input value={path} onChange={(e) => setPath(e.target.value)} placeholder="tenant_X/students/documents/foo.pdf" />
            </div>
            <div className="col-span-3 flex justify-end">
              <Button type="submit" disabled={!path || add.isPending}>
                <FilePlus2 className="h-4 w-4" />
                Add document
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documents ({docs.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!docs.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No documents yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {docs.map((d) => (
                <li key={d.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium text-indigo-dark">
                      {d.label || d.kind.replace(/_/g, " ")}
                    </p>
                    <p className="font-mono text-xs text-muted-foreground">{d.path}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {d.is_verified ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-teal-pale px-2 py-0.5 text-[11px] font-medium text-teal-dark">
                        <FileCheck2 className="h-3 w-3" />
                        Verified
                      </span>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => verify.mutate(d.id)}>
                        Verify
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => remove.mutate(d.id)}>
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

function HistoryTab({ s }: { s: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>History</CardTitle>
        <CardDescription>Phase 6 surfaces the basics; promotions + TC become a real timeline in Phase 7+.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Pair label="Admitted on" value={s.admission_date} />
            <Pair label="Previous school" value={s.previous_school} />
          </div>
          <div>
            <Pair label="Status" value={s.status} />
            <Pair label="Exit date" value={s.exit_date} />
            <Pair label="Remarks" value={s.remarks} />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
