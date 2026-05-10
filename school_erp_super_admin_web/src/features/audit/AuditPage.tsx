import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { globalAudit } from "@/features/schools/api";

export function AuditPage() {
  const [prefix, setPrefix] = useState("");
  const audit = useQuery({ queryKey: ["audit-global", prefix], queryFn: () => globalAudit(prefix || undefined) });

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 3 · Compliance</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Audit log</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Every super-admin action is recorded here. Filter by action prefix.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>Try <code className="font-mono">tenant.</code> or <code className="font-mono">plan.</code>.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-w-sm space-y-2">
            <Label>Action prefix</Label>
            <Input value={prefix} onChange={(e) => setPrefix(e.target.value)} placeholder="e.g. tenant.create" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {audit.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : audit.isError ? (
            <p className="px-6 py-4 text-sm text-destructive">Could not load the audit feed.</p>
          ) : !audit.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No matching events.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">When</th>
                  <th className="px-4 py-3">Tenant</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Summary</th>
                </tr>
              </thead>
              <tbody>
                {audit.data!.map((row) => (
                  <tr key={row.id} className="border-b last:border-b-0">
                    <td className="px-6 py-2 font-mono text-xs">{new Date(row.created_at).toLocaleString()}</td>
                    <td className="px-4 py-2">{row.tenant_id || "—"}</td>
                    <td className="px-4 py-2">{row.actor_email ?? "—"}</td>
                    <td className="px-4 py-2 font-mono text-xs text-saffron-dark">{row.action}</td>
                    <td className="px-4 py-2">{row.summary ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
