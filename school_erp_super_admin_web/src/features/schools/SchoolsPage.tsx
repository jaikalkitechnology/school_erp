import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pause, Play, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { activateTenant, listTenants, suspendTenant } from "./api";
import type { Tenant, TenantStatus } from "./types";

const STATUS_TONE: Record<TenantStatus, string> = {
  trial: "bg-marigold-pale text-marigold-dark",
  active: "bg-teal-pale text-teal-dark",
  suspended: "bg-saffron-pale text-saffron-darker",
  cancelled: "bg-muted text-muted-foreground",
};

export function SchoolsPage() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const tenants = useQuery({
    queryKey: ["tenants", search],
    queryFn: () => listTenants(search || undefined),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["tenants"] });
  const suspend = useMutation({ mutationFn: suspendTenant, onSuccess: invalidate });
  const activate = useMutation({ mutationFn: activateTenant, onSuccess: invalidate });

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
            Phase 3 · Multi-Tenant
          </p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">Schools</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Every school on Jaikalki gets its own subdomain, plan, branding, and isolated data.
          </p>
        </div>
        <Button asChild>
          <Link to="/schools/new">
            <Plus className="h-4 w-4" />
            Onboard school
          </Link>
        </Button>
      </header>

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, subdomain, or code"
          className="pl-9"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All schools ({tenants.data?.length ?? "…"})</CardTitle>
          <CardDescription>Click a row to drill in.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {tenants.isLoading ? (
            <p className="px-6 pb-6 text-sm text-muted-foreground">Loading…</p>
          ) : tenants.isError ? (
            <p className="px-6 pb-6 text-sm text-destructive">
              Could not reach the backend. Make sure the API is running on port 8000.
            </p>
          ) : (tenants.data?.length ?? 0) === 0 ? (
            <p className="px-6 pb-6 text-sm text-muted-foreground">
              No schools yet. Click <strong>Onboard school</strong> to add your first tenant.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-6 py-3">School</th>
                    <th className="px-4 py-3">Subdomain</th>
                    <th className="px-4 py-3">Plan</th>
                    <th className="px-4 py-3">Limits</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tenants.data!.map((t) => (
                    <TenantRow
                      key={t.id}
                      tenant={t}
                      onSuspend={() => suspend.mutate(t.id)}
                      onActivate={() => activate.mutate(t.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function TenantRow({
  tenant,
  onSuspend,
  onActivate,
}: {
  tenant: Tenant;
  onSuspend: () => void;
  onActivate: () => void;
}) {
  return (
    <tr className="border-b last:border-b-0 hover:bg-saffron-pale/30">
      <td className="px-6 py-3">
        <Link to={`/schools/${tenant.id}`} className="font-medium text-indigo-dark hover:underline">
          {tenant.school_name}
        </Link>
        <div className="text-xs text-muted-foreground">
          {[tenant.city, tenant.state].filter(Boolean).join(", ") || tenant.school_code}
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-saffron-dark">{tenant.subdomain}</td>
      <td className="px-4 py-3">{tenant.plan?.name ?? "—"}</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {tenant.student_limit || "∞"} students · {(tenant.storage_limit_mb / 1024).toFixed(0)}GB
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
            STATUS_TONE[tenant.status],
          )}
        >
          {tenant.status}
        </span>
      </td>
      <td className="px-6 py-3 text-right">
        {tenant.status === "suspended" ? (
          <Button variant="ghost" size="sm" onClick={onActivate}>
            <Play className="h-3.5 w-3.5" />
            Activate
          </Button>
        ) : tenant.status !== "cancelled" ? (
          <Button variant="ghost" size="sm" onClick={onSuspend}>
            <Pause className="h-3.5 w-3.5" />
            Suspend
          </Button>
        ) : null}
      </td>
    </tr>
  );
}
