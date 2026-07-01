import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listLoans, returnLoan, sweepOverdue, type LoanStatus } from "./api";
import { LOAN_TONE, LibraryHeader } from "./_shared";

/** Return-desk view. Filter open loans by borrower / copy, hit
 * Return. "Sweep overdue" recalculates fines for loans past their
 * due date. */
export function LibraryReturnBooksPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<LoanStatus | "open">("open");
  const [q, setQ] = useState("");

  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", statusFilter],
    queryFn: () =>
      listLoans({
        status_filter:
          statusFilter === "open" || statusFilter === undefined
            ? undefined
            : statusFilter,
      }),
  });

  // "open" is a client-side alias for active + overdue — the endpoint
  // doesn't expose that as a single option so we combine here.
  const filtered = useMemo(() => {
    const base =
      statusFilter === "open"
        ? loans.filter((l) => l.status === "active" || l.status === "overdue")
        : loans;
    if (!q.trim()) return base;
    const needle = q.trim().toLowerCase();
    return base.filter(
      (l) =>
        String(l.id) === needle ||
        String(l.copy_id) === needle ||
        String(l.borrower_id) === needle,
    );
  }, [loans, q, statusFilter]);

  const sweep = useMutation({
    mutationFn: sweepOverdue,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  const ret = useMutation({
    mutationFn: (loanId: number) => returnLoan({ loan_id: loanId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Return books"
        subtitle="Close out active loans. Sweep overdue recalculates fines against today's date."
      />
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Loans</CardTitle>
            <CardDescription>
              {filtered.length} matching {statusFilter} loans
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Input
              className="w-56"
              placeholder="Filter by loan / copy / borrower ID"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as LoanStatus | "open")}
            >
              <option value="open">Open (active + overdue)</option>
              <option value="active">Active</option>
              <option value="overdue">Overdue</option>
              <option value="returned">Returned</option>
              <option value="lost">Lost</option>
            </select>
            <Button
              variant="outline"
              onClick={() => sweep.mutate()}
              disabled={sweep.isPending}
            >
              <RefreshCw className="mr-1 h-4 w-4" />
              Sweep overdue
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No loans match.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Loan</th>
                  <th>Copy</th>
                  <th>Borrower</th>
                  <th>Issued</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Fine</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id} className="border-t border-saffron-pale">
                    <td className="py-2">#{l.id}</td>
                    <td>#{l.copy_id}</td>
                    <td>
                      {l.borrower_kind} #{l.borrower_id}
                    </td>
                    <td>{l.issued_on}</td>
                    <td>{l.due_on}</td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", LOAN_TONE[l.status])}>
                        {l.status}
                      </span>
                    </td>
                    <td>₹{l.fine_amount}</td>
                    <td className="text-right">
                      {l.status !== "returned" && l.status !== "lost" && (
                        <Button size="sm" variant="ghost" onClick={() => ret.mutate(l.id)}>
                          <RotateCcw className="mr-1 h-3 w-3" />
                          Return
                        </Button>
                      )}
                    </td>
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
