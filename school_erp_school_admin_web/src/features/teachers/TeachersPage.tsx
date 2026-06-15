import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listDepartments } from "@/features/setup/api";
import { StudentAvatar } from "@/features/students/StudentAvatar";
import { listTeachers, type EmploymentStatus } from "./api";

const STATUS_TONE: Record<EmploymentStatus, string> = {
  active: "bg-teal-pale text-teal-dark",
  on_leave: "bg-marigold-pale text-marigold-dark",
  resigned: "bg-muted text-muted-foreground",
};

export function TeachersPage() {
  const [q, setQ] = useState("");
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const [statusFilter, setStatusFilter] = useState<EmploymentStatus | "">("active");
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });

  const params = {
    q: q || undefined,
    department_id: departmentId === "" ? undefined : Number(departmentId),
    status: statusFilter === "" ? undefined : (statusFilter as EmploymentStatus),
    limit,
    offset,
  };
  const list = useQuery({ queryKey: ["teachers", params], queryFn: () => listTeachers(params) });

  const total = list.data?.total ?? 0;
  const showingTo = Math.min(offset + limit, total);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 7 · Staff</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">Teachers</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Onboard, assign subjects + classes, track workload + attendance.
          </p>
        </div>
        <Button asChild>
          <Link to="/teachers/onboard">
            <Plus className="h-4 w-4" />
            Onboard teacher
          </Link>
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>Search by name, employee number, phone, or email.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => { setQ(e.target.value); setOffset(0); }}
                placeholder="Asha / EMP-25-0001 / +9198…"
                className="pl-9"
              />
            </div>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={departmentId}
              onChange={(e) => { setDepartmentId(e.target.value ? Number(e.target.value) : ""); setOffset(0); }}
            >
              <option value="">All departments</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={statusFilter}
              onChange={(e) => { setStatusFilter((e.target.value || "") as EmploymentStatus | ""); setOffset(0); }}
            >
              <option value="">Any status</option>
              <option value="active">Active</option>
              <option value="on_leave">On leave</option>
              <option value="resigned">Resigned</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {total} {total === 1 ? "teacher" : "teachers"}
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {total > 0 && `showing ${offset + 1}–${showingTo}`}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : !list.data?.items.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">
              No teachers yet. <Link to="/teachers/onboard" className="text-saffron-dark">Onboard one</Link>.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="w-12 px-6 py-3">Photo</th>
                    <th className="px-4 py-3">Teacher</th>
                    <th className="px-4 py-3">Employee</th>
                    <th className="px-4 py-3">Designation</th>
                    <th className="px-4 py-3">Contact</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((t) => (
                    <tr key={t.id} className="border-b last:border-b-0 hover:bg-saffron-pale/30">
                      <td className="px-6 py-3">
                        <StudentAvatar
                          photoUrl={t.photo_url}
                          name={t.full_name}
                          size={36}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <Link to={`/teachers/${t.id}`} className="font-medium text-indigo-dark hover:underline">
                          {t.full_name}
                        </Link>
                        <div className="text-xs text-muted-foreground">
                          {t.is_class_teacher && (
                            <span className="mr-2 inline-flex items-center gap-1 text-teal-dark">
                              <Users className="h-3 w-3" />
                              class teacher
                            </span>
                          )}
                          {(t.qualifications || []).slice(0, 2).join(", ")}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-saffron-dark">{t.employee_no}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{t.designation ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {t.phone && <div className="font-mono">{t.phone}</div>}
                        {t.email}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
                          STATUS_TONE[t.employment_status],
                        )}>
                          {t.employment_status.replace(/_/g, " ")}
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
