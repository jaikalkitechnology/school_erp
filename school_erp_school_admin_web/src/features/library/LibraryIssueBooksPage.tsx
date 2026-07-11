import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Hand } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  issueLoan,
  listBooks,
  listCopies,
  listLoans,
  type BorrowerKind,
} from "./api";
import { LOAN_TONE, LibraryHeader } from "./_shared";

/** Issue-book desk. Two-step flow that stops the librarian from
 * typing a copy ID that doesn't exist (which was hitting a 404):
 *
 *   1. Search + pick the title.
 *   2. Pick an available copy of that title (only "available" copies
 *      are eligible; the rest are shown greyed out).
 *   3. Enter the borrower's admission ID + type + optional loan
 *      length, then Issue.
 *
 * Below the form, a live list of every currently-active loan. */
export function LibraryIssueBooksPage() {
  const qc = useQueryClient();

  // --- Step 1: book picker ------------------------------------------
  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });
  const [bookId, setBookId] = useState<number | null>(null);
  const activeBook = books.find((b) => b.id === bookId);

  // --- Step 2: copy picker (for the selected book) ------------------
  const { data: copies = [], isLoading: copiesLoading } = useQuery({
    queryKey: ["library-copies", bookId],
    queryFn: () => (bookId ? listCopies(bookId) : Promise.resolve([])),
    enabled: bookId !== null,
  });
  const [copyId, setCopyId] = useState<number | null>(null);
  const availableCopies = useMemo(
    () => copies.filter((c) => c.status === "available"),
    [copies],
  );

  // --- Step 3: borrower + issue -------------------------------------
  const [borrowerId, setBorrowerId] = useState("");
  const [borrowerKind, setBorrowerKind] = useState<BorrowerKind>("student");
  const [loanDays, setLoanDays] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const issue = useMutation({
    mutationFn: () =>
      issueLoan({
        copy_id: copyId!,
        borrower_kind: borrowerKind,
        borrower_id: Number(borrowerId),
        loan_days: loanDays ? Number(loanDays) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-loans"] });
      qc.invalidateQueries({ queryKey: ["library-copies", bookId] });
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setCopyId(null);
      setBorrowerId("");
      setLoanDays("");
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(
        typeof detail === "string"
          ? detail
          : "Could not issue this book. Check the copy is available and the borrower ID is right.",
      );
    },
  });

  // --- live active loans -------------------------------------------
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "active"],
    queryFn: () => listLoans({ status_filter: "active" }),
  });

  const canSubmit = copyId !== null && borrowerId.trim().length > 0 && !issue.isPending;

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Issue books"
        subtitle="Pick a title, then an available copy, then the borrower. No typing raw copy IDs — the picker only shows real, in-stock copies."
      />

      <div className="grid gap-6 md:grid-cols-[320px_1fr]">
        {/* Step 1: title */}
        <Card>
          <CardHeader>
            <CardTitle>1. Pick a title</CardTitle>
            <CardDescription>{books.length} in catalogue</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Search title / ISBN"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="max-h-[420px] space-y-1 overflow-y-auto">
              {books.length === 0 ? (
                <p className="text-sm text-muted-foreground">No books yet.</p>
              ) : (
                books.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => {
                      setBookId(b.id);
                      setCopyId(null);
                      setErrorMsg(null);
                    }}
                    className={cn(
                      "flex w-full flex-col rounded-md border px-3 py-2 text-left transition-colors",
                      bookId === b.id
                        ? "border-saffron bg-saffron-pale text-saffron-darker"
                        : "border-transparent hover:bg-muted",
                      b.available_copies === 0 && "opacity-60",
                    )}
                  >
                    <span className="text-sm font-semibold">{b.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {b.available_copies} of {b.total_copies} available
                    </span>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Steps 2 + 3: copy + borrower */}
        <div className="space-y-4">
          {activeBook === undefined ? (
            <Card>
              <CardContent className="py-16 text-center text-sm text-muted-foreground">
                Pick a title on the left to see its copies.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>2. Pick a copy</CardTitle>
                  <CardDescription>
                    {activeBook.title} · {availableCopies.length} available
                    {availableCopies.length !== copies.length &&
                      ` (${copies.length - availableCopies.length} out on loan)`}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {copiesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading copies…</p>
                  ) : availableCopies.length === 0 ? (
                    <p className="text-sm text-destructive">
                      No copies of this title are available right now.
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {availableCopies.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => {
                            setCopyId(c.id);
                            setErrorMsg(null);
                          }}
                          className={cn(
                            "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                            copyId === c.id
                              ? "border-saffron bg-saffron-pale text-saffron-darker"
                              : "border-input hover:bg-muted",
                          )}
                        >
                          <span className="block font-mono">{c.barcode}</span>
                          <span className="text-muted-foreground">
                            #{c.id}
                            {c.accession_number
                              ? ` · ${c.accession_number}`
                              : ""}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>3. Borrower</CardTitle>
                  <CardDescription>
                    Enter the student's admission number or the teacher's user
                    ID.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <Label>Borrower type</Label>
                    <select
                      className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                      value={borrowerKind}
                      onChange={(e) =>
                        setBorrowerKind(e.target.value as BorrowerKind)
                      }
                    >
                      <option value="student">Student</option>
                      <option value="teacher">Teacher</option>
                    </select>
                  </div>
                  <div>
                    <Label>Borrower ID</Label>
                    <Input
                      value={borrowerId}
                      onChange={(e) => setBorrowerId(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Loan days (blank = default)</Label>
                    <Input
                      value={loanDays}
                      onChange={(e) => setLoanDays(e.target.value)}
                    />
                  </div>
                  {errorMsg && (
                    <p className="col-span-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {errorMsg}
                    </p>
                  )}
                  <div className="col-span-3">
                    <Button
                      onClick={() => {
                        setErrorMsg(null);
                        issue.mutate();
                      }}
                      disabled={!canSubmit}
                    >
                      <Hand className="mr-1 h-4 w-4" />
                      Issue book
                    </Button>
                    {copyId === null && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Pick a copy above to enable the Issue button.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

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
