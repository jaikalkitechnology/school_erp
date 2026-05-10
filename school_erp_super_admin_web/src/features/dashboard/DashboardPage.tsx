import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { analyticsOverview, listTenants } from "@/features/schools/api";
import { Link } from "react-router-dom";

export function DashboardPage() {
  const overview = useQuery({ queryKey: ["analytics-overview"], queryFn: analyticsOverview });
  const recent = useQuery({ queryKey: ["tenants-recent"], queryFn: () => listTenants() });

  const tiles = overview.data
    ? [
        { label: "Schools", value: overview.data.total_tenants, hint: `${overview.data.active_tenants} active · ${overview.data.trial_tenants} trial` },
        { label: "MRR", value: `₹${Math.round(overview.data.mrr).toLocaleString("en-IN")}`, hint: "Across active subscriptions" },
        { label: "Students", value: overview.data.total_students.toLocaleString("en-IN"), hint: "Across all schools" },
        { label: "Teachers", value: overview.data.total_teachers.toLocaleString("en-IN"), hint: "Across all schools" },
      ]
    : Array.from({ length: 4 }, (_, i) => ({ label: ["Schools", "MRR", "Students", "Teachers"][i], value: "—", hint: "Loading…" }));

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 3 · Super Admin</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">
          Welcome, <em className="italic text-saffron">platform owner</em>.
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Live numbers across the entire fleet of schools.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((t) => (
          <Card key={t.label} className="border-saffron-pale">
            <CardHeader className="pb-2">
              <CardDescription className="text-[11px] uppercase tracking-[0.18em] text-saffron-dark">{t.label}</CardDescription>
              <CardTitle className="text-3xl">{t.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{t.hint}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By plan</CardTitle>
            <CardDescription>How many schools sit on each plan.</CardDescription>
          </CardHeader>
          <CardContent>
            <PlanBars data={overview.data?.by_plan ?? {}} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By state</CardTitle>
            <CardDescription>Geographic spread.</CardDescription>
          </CardHeader>
          <CardContent>
            <PlanBars data={overview.data?.by_state ?? {}} accent="teal" />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent schools</CardTitle>
          <CardDescription>Last 5 onboardings.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-6 py-3">School</th>
                <th className="px-4 py-3">Subdomain</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Joined</th>
              </tr>
            </thead>
            <tbody>
              {(recent.data ?? []).slice(0, 5).map((t) => (
                <tr key={t.id} className="border-b last:border-b-0 hover:bg-saffron-pale/30">
                  <td className="px-6 py-2">
                    <Link to={`/schools/${t.id}`} className="font-medium text-indigo-dark hover:underline">
                      {t.school_name}
                    </Link>
                    <span className="ml-2 text-xs text-muted-foreground">{t.school_code}</span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-saffron-dark">{t.subdomain}</td>
                  <td className="px-4 py-2 capitalize">{t.status}</td>
                  <td className="px-4 py-2 font-mono text-xs">{new Date(t.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {recent.isSuccess && recent.data!.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-sm text-muted-foreground">
                    No schools yet. <Link to="/schools/new" className="text-saffron-dark">Onboard one</Link>.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function PlanBars({ data, accent = "saffron" }: { data: Record<string, number>; accent?: "saffron" | "teal" }) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);
  if (!entries.length) return <p className="text-sm text-muted-foreground">No data yet.</p>;
  const max = Math.max(...entries.map(([, v]) => v));
  const colour = accent === "teal" ? "bg-teal" : "bg-saffron";
  return (
    <ul className="space-y-2">
      {entries.map(([label, value]) => (
        <li key={label} className="grid grid-cols-[120px_1fr_40px] items-center gap-3 text-sm">
          <span className="truncate font-medium capitalize text-indigo-dark">{label}</span>
          <span className="h-2 rounded-full bg-muted">
            <span className={`block h-full rounded-full ${colour}`} style={{ width: `${(value / max) * 100}%` }} />
          </span>
          <span className="text-right font-mono text-xs">{value}</span>
        </li>
      ))}
    </ul>
  );
}
