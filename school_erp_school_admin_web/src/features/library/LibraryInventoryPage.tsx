import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Flag, Play, ScanLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LibraryHeader, StatTile } from "./_shared";
import {
  completeVerification,
  getVerification,
  scanVerification,
  startVerification,
} from "./api";

/** Server-backed stock verification. Start a session, scan every copy's
 * barcode as you walk the shelves — each scan is persisted, so a page
 * reload (or a second device) resumes the same session. Missing = copies
 * on record that were never scanned. Complete closes the session and
 * records it in the audit log. */
export function LibraryInventoryPage() {
  const qc = useQueryClient();
  const { data: state } = useQuery({
    queryKey: ["library-verification"],
    queryFn: getVerification,
    refetchInterval: 8000, // pick up scans from a second device
  });
  const [scan, setScan] = useState("");
  const [lastMsg, setLastMsg] = useState<string | null>(null);

  const session = state?.session ?? null;

  const start = useMutation({
    mutationFn: startVerification,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-verification"] }),
  });

  const doScan = useMutation({
    mutationFn: (barcode: string) => scanVerification(session!.id, barcode),
    onSuccess: (res) => {
      setLastMsg(
        res.recognised
          ? `✓ ${res.barcode}`
          : `⚠ ${res.barcode} — not a known copy`,
      );
      setScan("");
      qc.invalidateQueries({ queryKey: ["library-verification"] });
    },
  });

  const complete = useMutation({
    mutationFn: () => completeVerification(session!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-verification"] }),
  });

  const total = state?.total_copies ?? 0;
  const scanned = state?.scanned ?? 0;
  const missing = state?.missing ?? 0;

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Inventory verification"
        subtitle="Start a session and scan every copy's barcode. Progress is saved on the server — reload or hand off to another device and continue where you left off."
      />

      {session === null ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <p className="text-sm text-muted-foreground">
              No verification in progress.
            </p>
            <Button onClick={() => start.mutate()} disabled={start.isPending}>
              <Play className="mr-1 h-4 w-4" /> Start verification
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <StatTile label="On record" value={total} />
            <StatTile label="Scanned" value={scanned} tone="teal" />
            <StatTile
              label="Missing"
              value={missing}
              tone={missing > 0 ? "destructive" : "teal"}
            />
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Scan copies</CardTitle>
                <CardDescription>
                  Session #{session.id} · started{" "}
                  {session.started_at
                    ? new Date(session.started_at).toLocaleString()
                    : "—"}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                onClick={() => complete.mutate()}
                disabled={complete.isPending}
              >
                <Flag className="mr-1 h-4 w-4" /> Complete
              </Button>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (scan.trim()) doScan.mutate(scan.trim());
                }}
                className="mb-4 flex items-center gap-2"
              >
                <ScanLine className="h-4 w-4 text-muted-foreground" />
                <Input
                  autoFocus
                  value={scan}
                  onChange={(e) => setScan(e.target.value)}
                  placeholder="Scan or paste a barcode…"
                />
                <Button type="submit" disabled={!scan.trim() || doScan.isPending}>
                  Record
                </Button>
              </form>
              {lastMsg && (
                <p className="mb-3 text-sm text-muted-foreground">{lastMsg}</p>
              )}

              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                Scanned this session ({scanned})
              </p>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                {(state?.scans ?? []).map((s) => (
                  <div
                    key={s.barcode}
                    className={
                      "flex items-center gap-2 rounded-md border px-3 py-2 text-xs " +
                      (s.found
                        ? "border-teal-dark bg-teal-pale text-teal-dark"
                        : "border-destructive bg-destructive/10 text-destructive")
                    }
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-mono">{s.barcode}</span>
                    {!s.found && <span className="ml-auto">unknown</span>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
