import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface HealthResponse {
  status: string;
  service: string;
  database: string;
  redis: string;
  environment: string;
  version: string;
}

const stats = [
  { label: "Active schools", value: "—", hint: "Onboard your first tenant in Phase 3" },
  { label: "Subscribed seats", value: "—", hint: "Plans seeded in Phase 1" },
  { label: "MRR (₹)", value: "—", hint: "Billing dashboard ships in Phase 21" },
  { label: "Storage used", value: "—", hint: "Per-tenant quota in Phase 1" },
];

export function DashboardPage() {
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
            Phase 0 · Foundation
          </p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">
            Welcome, <em className="italic text-saffron">platform owner</em>.
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            The console wireframe is live with the Jaikalki design system. Real data lights up as
            phases land.
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
          <CardTitle>Backend connectivity</CardTitle>
          <CardDescription>Live ping to the FastAPI service.</CardDescription>
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
