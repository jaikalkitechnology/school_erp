import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listLoans, renewLoan } from "./api";
import { LOAN_TONE, LibraryHeader } from "./_shared";

/** Renew due dates on active or overdue loans without a full
 * return-then-reissue. The librarian filters the loan table, picks
 * a row, and clicks Renew (default: extend by 7 days). Backend
 * blocks the renewal if the book has an outstanding reservation
 * from another borrower. */
export function LibraryRenewBooksPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [extraDays, setExtraDays] = useState("7");
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "renewable"],
    queryFn: () => listLoans({}),
  });

  const renewable = useMemo(
    () => loans.filter((l) => l.status === "active" || l.status === "overdue"),
    [loans],
  );

  const filtered = useMemo(() => {
    if (!q.trim()) return renewable;
    const needle = q.trim().toLowerCase();
    return renewable.filter(
      (l) =>
        String(l.id) === needle ||
        String(l.copy_id) === needle ||
        String(l.borrower_id) === needle,
    );
  }, [renewable, q]);

  const renew = useMutation({
    mutationFn: (loanId: number) => renewLoan(loanId, Number(extraDays) || 7),
    onSuccess: (data) => {
      setFeedback({
        ok: true,
        msg: `Loan #${data.loan_id} renewed — new due date ${data.new_due_on}.`,
      });
      qc.invalidateQueries({ queryKey: ["library-loans"] });
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setFeedback({
        ok: false,
        msg: typeof detail === "string" ? detail : "Could not renew this loan.",
      });
    },
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Renew books"
        subtitle="Extend the due date on an active or overdue loan. Blocked if someone else has the title reserved."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Renewable loans</CardTitle>
            <CardDescription>{filtered.length} of {renewable.length} shown</CardDescription>
          </div>
          <div className="flex items-center gap-3">
            <Input
              className="w-56"
              placeholder="Filter by loan / copy / borrower ID"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Extend by</span>
              <Input
                className="w-16"
                value={extraDays}
                onChange={(e) => setExtraDays(e.target.value)}
              />
              <span className="text-xs text-muted-foreground">days</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {feedback && (
            <p
              className={cn(
                "mb-3 rounded-md px-3 py-2 text-sm",
                feedback.ok
                  ? "bg-teal-pale text-teal-dark"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              {feedback.msg}
            </p>
          )}
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing to renew.</p>
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
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id} className="border-t border-saffron-pale">
                    <td className="py-2">#{l.id}</td>
                    <td>#{l.copy_id}</td>
                    <td>{l.borrower_kind} #{l.borrower_id}</td>
                    <td>{l.issued_on}</td>
                    <td>{l.due_on}</td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", LOAN_TONE[l.status])}>
                        {l.status}
                      </span>
                    </td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        onClick={() => {
                          setFeedback(null);
                          renew.mutate(l.id);
                        }}
                        disabled={renew.isPending}
                      >
                        <RefreshCw className="mr-1 h-3 w-3" /> Renew
                      </Button>
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
