import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { CalendarDays, GraduationCap, Layers, ShieldAlert, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchDashboard } from "@/features/setup/api";
import { useAuth } from "@/stores/auth";

const today = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
}).format(new Date());

export function DashboardPage() {
  const user = useAuth((s) => s.user);
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });

  const tiles = dashboard.data
    ? [
        { label: "Students", value: dashboard.data.students_count, icon: GraduationCap, hint: "Active roster" },
        { label: "Teachers", value: dashboard.data.teachers_count, icon: Users, hint: "Class + Subject teachers" },
        { label: "Classes", value: `${dashboard.data.classes_count} · ${dashboard.data.sections_count} sec`, icon: Layers, hint: "Across all stages" },
        {
          label: "Storage",
          value: `${dashboard.data.storage_used_mb.toFixed(0)} MB`,
          icon: ShieldAlert,
          hint: `of ${(dashboard.data.storage_limit_mb / 1024).toFixed(0)}GB plan`,
        },
      ]
    : Array.from({ length: 4 }, (_, i) => ({
        label: ["Students", "Teachers", "Classes", "Storage"][i],
        value: "—",
        icon: GraduationCap,
        hint: dashboard.isError ? "Backend unreachable" : "Loading…",
      }));

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">{today}</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">
            Namaste, <em className="italic text-saffron">{user?.full_name?.split(" ")[0] ?? "Admin"}</em>.
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            {dashboard.data?.school_name ?? user?.school_name ?? "Your school"} — quick health check.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/settings">School settings</Link>
        </Button>
      </header>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((t) => {
          const Icon = t.icon;
          return (
            <Card key={t.label} className="border-saffron-pale">
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-saffron-dark">
                  <Icon className="h-3.5 w-3.5" />
                  {t.label}
                </CardDescription>
                <CardTitle className="text-3xl">{t.value}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{t.hint}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarDays className="h-5 w-5 text-saffron" />
              Active academic year
            </CardTitle>
            <CardDescription>Set in <Link to="/academic" className="text-saffron-dark">Academic setup</Link>.</CardDescription>
          </CardHeader>
          <CardContent>
            {dashboard.data?.active_year ? (
              <div className="space-y-3">
                <div>
                  <p className="font-display text-xl text-indigo-dark">{dashboard.data.active_year.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {dashboard.data.active_year.start_date} → {dashboard.data.active_year.end_date}
                  </p>
                </div>
                <ul className="space-y-1 text-sm">
                  {dashboard.data.active_year.terms.map((t) => (
                    <li key={t.id} className="flex justify-between rounded-md border border-saffron-pale px-3 py-2">
                      <span>{t.name}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {t.start_date} → {t.end_date}
                      </span>
                    </li>
                  ))}
                  {!dashboard.data.active_year.terms.length && (
                    <li className="text-xs text-muted-foreground">No terms yet — add some on the academic page.</li>
                  )}
                </ul>
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-saffron-pale p-4 text-sm text-muted-foreground">
                No active academic year. Create one and mark it active in{" "}
                <Link to="/academic" className="text-saffron-dark">Academic setup</Link>.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>Jump back to where you left off.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <QuickLink to="/org" label="Departments / Classes / Subjects" hint={`${dashboard.data?.departments_count ?? 0} departments · ${dashboard.data?.subjects_count ?? 0} subjects`} />
            <QuickLink to="/academic" label="Academic year, terms, holidays" hint={dashboard.data?.active_year ? `Active: ${dashboard.data.active_year.name}` : "No active year yet"} />
            <QuickLink to="/students" label="Students (Phase 6)" hint="Coming up next" />
            <QuickLink to="/teachers" label="Teachers (Phase 7)" hint="Coming up next" />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function QuickLink({ to, label, hint }: { to: string; label: string; hint: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between rounded-md border border-saffron-pale px-3 py-2 text-sm transition hover:bg-saffron-pale/40"
    >
      <span className="font-medium text-indigo-dark">{label}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </Link>
  );
}
