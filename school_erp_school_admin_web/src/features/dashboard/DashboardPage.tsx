import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

interface HealthResponse {
  status: string;
  service: string;
  database: string;
  redis: string;
}

const stats = [
  { label: "Students", value: "—", hint: "Imports begin in Phase 6" },
  { label: "Teachers", value: "—", hint: "Onboarding in Phase 7" },
  { label: "Today's attendance", value: "—", hint: "Phase 9 attendance module" },
  { label: "Fees due (₹)", value: "—", hint: "Phase 11 fees module" },
];

const today = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
}).format(new Date());

export function DashboardPage() {
  const user = useAuth((s) => s.user);
  const health = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => (await api.get("/v1/health")).data,
    refetchInterval: 15_000,
  });

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
            {today}
          </p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">
            Namaste, <em className="italic text-saffron">{user?.name?.split(" ")[0] ?? "Admin"}</em>.
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Your school cockpit. Modules light up phase by phase — Phase 0 ships the design system
            and routing.
          </p>
        </div>
        <div className="rounded-full border border-saffron-pale bg-warm-white px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-indigo-dark shadow-sm">
          API · {health.data?.status ?? (health.isError ? "unreachable" : "checking…")}
        </div>
      </header>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label} className="border-saffron-pale">
            <CardHeader className="pb-2">
              <CardDescription className="text-[11px] uppercase tracking-[0.18em] text-saffron-dark">
                {s.label}
              </CardDescription>
              <CardTitle className="text-3xl">{s.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{s.hint}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Connectivity</CardTitle>
          <CardDescription>
            Health probe to the FastAPI backend ({user?.tenant_subdomain ?? "tenant"} scope).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-md bg-indigo-dark px-4 py-3 font-mono text-xs text-marigold-pale">
            {JSON.stringify(health.data ?? { status: "loading" }, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
