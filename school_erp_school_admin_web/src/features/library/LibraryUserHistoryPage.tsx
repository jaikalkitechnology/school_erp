import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listLoans, type BorrowerKind } from "./api";
import { LOAN_TONE, LibraryHeader, StatTile } from "./_shared";

/** User loan history — punch in a borrower kind + ID and see every
 * loan they've ever taken, past + present. Used at the desk when
 * chasing fines or investigating a lost-copy claim. */
export function LibraryUserHistoryPage() {
  const [borrowerKind, setBorrowerKind] = useState<BorrowerKind>("student");
  const [borrowerIdInput, setBorrowerIdInput] = useState("");
  const [submitted, setSubmitted] = useState<{ kind: BorrowerKind; id: number } | null>(null);

  const { data: loans = [], isLoading } = useQuery({
    queryKey: ["library-loans-history", submitted?.kind, submitted?.id],
    queryFn: () =>
      submitted
        ? listLoans({
            borrower_kind: submitted.kind,
            borrower_id: submitted.id,
          })
        : Promise.resolve([]),
    enabled: submitted !== null,
  });

  const totalFine = loans.reduce((sum, l) => sum + (l.fine_amount ?? 0), 0);
  const totalPaid = loans.reduce((sum, l) => sum + (l.fine_paid ?? 0), 0);
  const outstanding = Math.max(0, totalFine - totalPaid);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const id = Number(borrowerIdInput);
    if (!id) return;
    setSubmitted({ kind: borrowerKind, id });
  };

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="User history"
        subtitle="Look up every loan a specific student or teacher has ever taken."
      />
      <Card>
        <CardHeader>
          <CardTitle>Look up borrower</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <Label>Borrower type</Label>
              <select
                className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={borrowerKind}
                onChange={(e) => setBorrowerKind(e.target.value as BorrowerKind)}
              >
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
              </select>
            </div>
            <div>
              <Label>Borrower ID</Label>
              <Input
                value={borrowerIdInput}
                onChange={(e) => setBorrowerIdInput(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="h-9 rounded-md bg-saffron px-4 text-sm font-medium text-warm-white hover:bg-saffron-dark"
              >
                Show history
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      {submitted && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <StatTile label="Loans on record" value={loans.length} />
            <StatTile
              label="Currently out"
              value={loans.filter((l) => l.status === "active" || l.status === "overdue").length}
              tone="marigold"
            />
            <StatTile label="Total fines" value={`₹${totalFine}`} tone="saffron" />
            <StatTile
              label="Outstanding"
              value={`₹${outstanding}`}
              tone={outstanding > 0 ? "destructive" : "teal"}
            />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Loan history</CardTitle>
              <CardDescription>
                {isLoading
                  ? "Loading…"
                  : `${submitted.kind} #${submitted.id} · ${loans.length} loans`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loans.length === 0 && !isLoading ? (
                <p className="text-sm text-muted-foreground">
                  No loans on record for this borrower.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="py-2">Loan</th>
                      <th>Copy</th>
                      <th>Issued</th>
                      <th>Due</th>
                      <th>Returned</th>
                      <th>Status</th>
                      <th>Fine (due / paid)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loans.map((l) => (
                      <tr key={l.id} className="border-t border-saffron-pale">
                        <td className="py-2">#{l.id}</td>
                        <td>#{l.copy_id}</td>
                        <td>{l.issued_on}</td>
                        <td>{l.due_on}</td>
                        <td>{l.returned_on ?? "—"}</td>
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
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
