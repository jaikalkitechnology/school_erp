import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, KeyRound, Pause, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { AdminLoginCard } from "./AdminLoginCard";
import {
  activateTenant,
  changePlan,
  extendTrial,
  getTenant,
  listPlans,
  suspendTenant,
  tenantAudit,
  tenantUsage,
  updateTenant,
} from "./api";

const TABS = ["Info", "Usage", "Audit"] as const;
type Tab = (typeof TABS)[number];

export function TenantDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const tenant = useQuery({ queryKey: ["tenant", id], queryFn: () => getTenant(id), enabled: !Number.isNaN(id) });
  const usage = useQuery({ queryKey: ["tenant-usage", id], queryFn: () => tenantUsage(id), enabled: !Number.isNaN(id) });
  const audit = useQuery({ queryKey: ["tenant-audit", id], queryFn: () => tenantAudit(id), enabled: !Number.isNaN(id) });
  const plans = useQuery({ queryKey: ["plans"], queryFn: listPlans });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["tenant", id] });
    qc.invalidateQueries({ queryKey: ["tenant-usage", id] });
    qc.invalidateQueries({ queryKey: ["tenant-audit", id] });
    qc.invalidateQueries({ queryKey: ["tenants"] });
  };

  const suspend = useMutation({ mutationFn: () => suspendTenant(id), onSuccess: invalidate });
  const activate = useMutation({ mutationFn: () => activateTenant(id), onSuccess: invalidate });
  const extend = useMutation({
    mutationFn: ({ days, reason }: { days: number; reason?: string }) => extendTrial(id, days, reason),
    onSuccess: invalidate,
  });
  const upgrade = useMutation({
    mutationFn: (plan_code: string) => changePlan(id, plan_code),
    onSuccess: invalidate,
  });

  const [tab, setTab] = useState<Tab>("Info");

  if (tenant.isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (tenant.isError || !tenant.data) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-destructive">Could not load this school.</p>
        </CardContent>
      </Card>
    );
  }

  const t = tenant.data;
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/schools")}>
          <ArrowLeft className="h-4 w-4" />
          All schools
        </Button>
        <div className="ml-auto flex gap-2">
          {t.status === "suspended" ? (
            <Button variant="outline" onClick={() => activate.mutate()}>
              <Play className="h-4 w-4" />
              Activate
            </Button>
          ) : (
            <Button variant="outline" onClick={() => suspend.mutate()}>
              <Pause className="h-4 w-4" />
              Suspend
            </Button>
          )}
        </div>
      </div>

      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          {t.subdomain}.jaikalki.com
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">{t.school_name}</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          {t.school_code} · {[t.city, t.state].filter(Boolean).join(", ") || "Location not set"} ·{" "}
          <span className="font-medium uppercase">{t.status}</span>
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

      {tab === "Info" && <InfoTab tenant={t} />}
      {tab === "Info" && <AdminLoginCard tenant={t} />}
      {tab === "Usage" && <UsageTab usage={usage.data} loading={usage.isLoading} />}
      {tab === "Audit" && <AuditTab rows={audit.data ?? []} loading={audit.isLoading} />}

      {tab === "Info" && (
        <PlanCard
          currentPlanId={t.plan_id ?? null}
          plans={plans.data ?? []}
          onChange={(code) => upgrade.mutate(code)}
          onExtend={(days, reason) => extend.mutate({ days, reason })}
          changing={upgrade.isPending}
          extending={extend.isPending}
        />
      )}
    </div>
  );
}

function InfoTab({ tenant }: { tenant: ReturnType<typeof getTenant> extends Promise<infer T> ? T : never }) {
  const qc = useQueryClient();
  const [school_name, setName] = useState(tenant.school_name);
  const [city, setCity] = useState(tenant.city ?? "");
  const [state, setState] = useState(tenant.state ?? "");
  const [primary_color, setPrimary] = useState(tenant.primary_color);
  const [secondary_color, setSecondary] = useState(tenant.secondary_color);

  const save = useMutation({
    mutationFn: () => updateTenant(tenant.id, { school_name, city, state, primary_color, secondary_color }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenant", tenant.id] });
      qc.invalidateQueries({ queryKey: ["tenants"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>School info</CardTitle>
        <CardDescription>Edit the school's display details.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label>School name</Label>
          <Input value={school_name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>City</Label>
          <Input value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>State</Label>
          <Input value={state} onChange={(e) => setState(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Primary colour</Label>
          <Input value={primary_color} onChange={(e) => setPrimary(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Secondary colour</Label>
          <Input value={secondary_color} onChange={(e) => setSecondary(e.target.value)} />
        </div>
        <div className="col-span-2 flex justify-end">
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function UsageTab({ usage, loading }: { usage: any; loading: boolean }) {
  if (loading || !usage) return <p className="text-sm text-muted-foreground">Loading usage…</p>;
  const tiles = [
    { label: "Storage used", value: `${usage.storage_used_mb.toFixed(1)} / ${usage.storage_limit_mb} MB`, hint: `${usage.storage_used_pct}% of plan` },
    { label: "Users", value: usage.users_count, hint: "Across all roles" },
    { label: "Student cap", value: usage.student_limit || "Unlimited", hint: "Plan limit" },
    { label: "Teacher cap", value: usage.teacher_limit || "Unlimited", hint: "Plan limit" },
  ];
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {tiles.map((t) => (
        <Card key={t.label} className="border-saffron-pale">
          <CardHeader className="pb-2">
            <CardDescription className="text-[11px] uppercase tracking-[0.18em] text-saffron-dark">{t.label}</CardDescription>
            <CardTitle className="text-2xl">{t.value}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">{t.hint}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AuditTab({ rows, loading }: { rows: any[]; loading: boolean }) {
  if (loading) return <p className="text-sm text-muted-foreground">Loading audit log…</p>;
  if (!rows.length) return <p className="text-sm text-muted-foreground">No audit events yet.</p>;
  return (
    <Card>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-6 py-3">When</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Summary</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b last:border-b-0">
                <td className="px-6 py-2 font-mono text-xs">{new Date(row.created_at).toLocaleString()}</td>
                <td className="px-4 py-2">{row.actor_email ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-xs text-saffron-dark">{row.action}</td>
                <td className="px-4 py-2">{row.summary ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function PlanCard({
  currentPlanId,
  plans,
  onChange,
  onExtend,
  changing,
  extending,
}: {
  currentPlanId: number | null;
  plans: { id: number; code: string; name: string; monthly_price: number }[];
  onChange: (code: string) => void;
  onExtend: (days: number, reason?: string) => void;
  changing: boolean;
  extending: boolean;
}) {
  const current = useMemo(() => plans.find((p) => p.id === currentPlanId), [plans, currentPlanId]);
  const [days, setDays] = useState(14);
  const [reason, setReason] = useState("");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Plan</CardTitle>
          <CardDescription>Currently on <strong>{current?.name ?? "no plan"}</strong>.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {plans.map((p) => (
              <button
                key={p.id}
                type="button"
                disabled={changing}
                onClick={() => onChange(p.code)}
                className={cn(
                  "rounded-md border p-3 text-left",
                  current?.id === p.id ? "border-saffron bg-saffron-pale" : "border-border hover:border-saffron-light",
                )}
              >
                <p className="text-xs uppercase tracking-wider text-saffron-dark">{p.code}</p>
                <p className="font-display text-base text-indigo-dark">{p.name}</p>
                <p className="text-xs text-muted-foreground">₹{p.monthly_price}/mo</p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Extend trial</CardTitle>
          <CardDescription>Bumps the subscription end-date.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              type="number"
              min={1}
              max={180}
              value={days}
              onChange={(e) => setDays(Math.max(1, Math.min(180, Number(e.target.value) || 1)))}
              className="w-32"
            />
            <Input
              placeholder="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="flex-1"
            />
            <Button onClick={() => onExtend(days, reason || undefined)} disabled={extending}>
              <RefreshCw className="h-4 w-4" />
              Extend
            </Button>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <KeyRound className="h-3 w-3" /> Plan upgrades + extensions are written to the audit log.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
