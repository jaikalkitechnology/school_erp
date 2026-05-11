import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import { listStudents, type StudentStatus } from "./api";

const STATUS_TONE: Record<StudentStatus, string> = {
  active: "bg-teal-pale text-teal-dark",
  inactive: "bg-muted text-muted-foreground",
  transferred: "bg-marigold-pale text-marigold-dark",
  passed_out: "bg-saffron-pale text-saffron-darker",
};

export function StudentsPage() {
  const [q, setQ] = useState("");
  const [classId, setClassId] = useState<number | "">("");
  const [sectionId, setSectionId] = useState<number | "">("");
  const [statusFilter, setStatusFilter] = useState<StudentStatus | "">("active");
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const params = {
    q: q || undefined,
    class_def_id: classId === "" ? undefined : Number(classId),
    section_id: sectionId === "" ? undefined : Number(sectionId),
    status: statusFilter === "" ? undefined : (statusFilter as StudentStatus),
    limit,
    offset,
  };
  const list = useQuery({ queryKey: ["students", params], queryFn: () => listStudents(params) });

  const classMap = useMemo(
    () => new Map((classes.data ?? []).map((c) => [c.id, c.name])),
    [classes.data],
  );

  const total = list.data?.total ?? 0;
  const showingTo = Math.min(offset + limit, total);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 6 · SIS</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">Students</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Search by name, admission number, or parent contact. Drill in for the full record.
          </p>
        </div>
        <Button asChild>
          <Link to="/students/admit">
            <Plus className="h-4 w-4" />
            Admit student
          </Link>
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>Combine free-text and class/section/status.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => { setQ(e.target.value); setOffset(0); }}
                placeholder="Name / adm.no / phone"
                className="pl-9"
              />
            </div>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={classId}
              onChange={(e) => { setClassId(e.target.value ? Number(e.target.value) : ""); setSectionId(""); setOffset(0); }}
            >
              <option value="">All classes</option>
              {(classes.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={sectionId}
              onChange={(e) => { setSectionId(e.target.value ? Number(e.target.value) : ""); setOffset(0); }}
            >
              <option value="">All sections</option>
              {(sections.data ?? [])
                .filter((s) => classId === "" || s.class_def_id === Number(classId))
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {classMap.get(s.class_def_id) ?? "?"} · {s.name}
                  </option>
                ))}
            </select>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={statusFilter}
              onChange={(e) => { setStatusFilter((e.target.value || "") as StudentStatus | ""); setOffset(0); }}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="transferred">Transferred</option>
              <option value="passed_out">Passed out</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {total} {total === 1 ? "student" : "students"}
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {total > 0 && `showing ${offset + 1}–${showingTo}`}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : list.isError ? (
            <p className="px-6 py-4 text-sm text-destructive">Could not load students.</p>
          ) : !list.data?.items.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">
              Nothing matches. Try a wider filter or{" "}
              <Link to="/students/admit" className="text-saffron-dark">admit a student</Link>.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-6 py-3">Student</th>
                    <th className="px-4 py-3">Admission</th>
                    <th className="px-4 py-3">Class</th>
                    <th className="px-4 py-3">Parent</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((s) => (
                    <tr key={s.id} className="border-b last:border-b-0 hover:bg-saffron-pale/30">
                      <td className="px-6 py-3">
                        <Link to={`/students/${s.id}`} className="font-medium text-indigo-dark hover:underline">
                          {s.full_name}
                        </Link>
                        <div className="text-xs text-muted-foreground">
                          {[s.gender, s.date_of_birth].filter(Boolean).join(" · ")}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-saffron-dark">{s.admission_number}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {s.current_class_label ??
                          (s.class_def_id ? classMap.get(s.class_def_id) ?? "?" : "—")}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {s.father_name || s.mother_name || s.guardian_name || "—"}
                        {s.parent_phone && <div className="font-mono">{s.parent_phone}</div>}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
                            STATUS_TONE[s.status],
                          )}
                        >
                          {s.status.replace(/_/g, " ")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {total > limit && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Previous
          </Button>
          <Button variant="outline" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
