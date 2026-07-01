import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Hand } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { issueLoan, listLoans, type BorrowerKind } from "./api";
import { LOAN_TONE, LibraryHeader } from "./_shared";

/** Issue-book desk view. Scan the copy barcode + borrower ID, hit
 * Issue. Below, a live list of only the *active* loans so the
 * librarian sees today's outstanding checkouts at a glance. */
export function LibraryIssueBooksPage() {
  const qc = useQueryClient();
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "active"],
    queryFn: () => listLoans({ status_filter: "active" }),
  });

  const [copyId, setCopyId] = useState("");
  const [borrowerId, setBorrowerId] = useState("");
  const [borrowerKind, setBorrowerKind] = useState<BorrowerKind>("student");
  const [loanDays, setLoanDays] = useState("");

  const issue = useMutation({
    mutationFn: () =>
      issueLoan({
        copy_id: Number(copyId),
        borrower_kind: borrowerKind,
        borrower_id: Number(borrowerId),
        loan_days: loanDays ? Number(loanDays) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-loans"] });
      setCopyId("");
      setBorrowerId("");
      setLoanDays("");
    },
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Issue books"
        subtitle="Loan a copy to a student or teacher."
      />

      <Card>
        <CardHeader>
          <CardTitle>New issue</CardTitle>
          <CardDescription>Scan / type the copy ID and borrower's admission number.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-4 gap-3">
          <div>
            <Label>Copy ID</Label>
            <Input value={copyId} onChange={(e) => setCopyId(e.target.value)} />
          </div>
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
            <Input value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)} />
          </div>
          <div>
            <Label>Loan days (blank = default)</Label>
            <Input value={loanDays} onChange={(e) => setLoanDays(e.target.value)} />
          </div>
          <div className="col-span-4">
            <Button
              onClick={() => issue.mutate()}
              disabled={!copyId || !borrowerId || issue.isPending}
            >
              <Hand className="mr-1 h-4 w-4" />
              Issue book
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active loans</CardTitle>
          <CardDescription>{loans.length} books currently issued</CardDescription>
        </CardHeader>
        <CardContent>
          {loans.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing checked out right now.</p>
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
                </tr>
              </thead>
              <tbody>
                {loans.map((l) => (
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
