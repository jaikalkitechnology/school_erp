import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listLoans, returnLoan, sweepOverdue } from "./api";
import { LOAN_TONE, LibraryHeader, StatTile } from "./_shared";

/** Fine-management desk. Shows every loan with an unpaid fine
 * balance (fine_amount > fine_paid), lets the librarian record a
 * payment via the return endpoint (or waive by paying 0 and marking
 * returned). Overdue-but-still-active loans also appear so the
 * librarian can see impending fines. */
export function LibraryFineManagementPage() {
  const qc = useQueryClient();
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "all-for-fines"],
    queryFn: () => listLoans({}),
  });

  const withFines = useMemo(
    () => loans.filter((l) => l.fine_amount > l.fine_paid),
    [loans],
  );

  const totalOutstanding = useMemo(
    () => withFines.reduce((sum, l) => sum + (l.fine_amount - l.fine_paid), 0),
    [withFines],
  );

  const [amounts, setAmounts] = useState<Record<number, string>>({});

  const sweep = useMutation({
    mutationFn: sweepOverdue,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  const collect = useMutation({
    mutationFn: (payload: { loanId: number; amount: number }) =>
      returnLoan({ loan_id: payload.loanId, fine_paid: payload.amount }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Fine management"
        subtitle="Collect or waive overdue fines. Only loans with a positive balance appear."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label="Loans with fines" value={withFines.length} tone="saffron" />
        <StatTile label="Total outstanding" value={`₹${totalOutstanding}`} tone="destructive" />
        <div className="flex items-center">
          <Button variant="outline" onClick={() => sweep.mutate()} disabled={sweep.isPending}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Recalculate fines
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Outstanding fines</CardTitle>
          <CardDescription>
            {withFines.length === 0
              ? "Nothing to collect right now."
              : "Enter the amount collected — the loan will be marked returned."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {withFines.length === 0 ? null : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Loan</th>
                  <th>Copy</th>
                  <th>Borrower</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Fine (due / paid)</th>
                  <th>Collect ₹</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {withFines.map((l) => {
                  const owed = l.fine_amount - l.fine_paid;
                  const amt = amounts[l.id] ?? String(owed);
                  return (
                    <tr key={l.id} className="border-t border-saffron-pale">
                      <td className="py-2">#{l.id}</td>
                      <td>#{l.copy_id}</td>
                      <td>
                        {l.borrower_kind} #{l.borrower_id}
                      </td>
                      <td>{l.due_on}</td>
                      <td>
                        <span
                          className={cn(
                            "rounded px-2 py-0.5 text-xs",
                            LOAN_TONE[l.status],
                          )}
                        >
                          {l.status}
                        </span>
                      </td>
                      <td>
                        ₹{l.fine_amount} / ₹{l.fine_paid}
                      </td>
                      <td className="w-32">
                        <Input
                          type="number"
                          min={0}
                          max={owed}
                          value={amt}
                          onChange={(e) => {
                            // Clamp 0..owed so you can't collect a
                            // negative amount or more than what's due.
                            const n = Math.min(
                              owed,
                              Math.max(0, Number(e.target.value) || 0),
                            );
                            setAmounts({ ...amounts, [l.id]: String(n) });
                          }}
                        />
                      </td>
                      <td className="text-right">
                        <Button
                          size="sm"
                          onClick={() =>
                            collect.mutate({
                              loanId: l.id,
                              amount: Math.min(owed, Math.max(0, Number(amt) || 0)),
                            })
                          }
                          disabled={collect.isPending || !(Number(amt) > 0)}
                        >
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Collect
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
