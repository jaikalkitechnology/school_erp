import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  cancelReservation,
  createReservation,
  listBooks,
  listReservations,
  type BorrowerKind,
} from "./api";
import { LibraryHeader, RES_TONE } from "./_shared";

/** Reservations — the librarian (or a student at the desk) can
 * queue for a title that's currently on loan. When a copy comes
 * back, the reservation flips to "ready" and the borrower can pick
 * it up. */
export function LibraryReservationsPage() {
  const qc = useQueryClient();

  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });
  const [bookId, setBookId] = useState<number | null>(null);
  const activeBook = books.find((b) => b.id === bookId);

  const [borrowerKind, setBorrowerKind] = useState<BorrowerKind>("student");
  const [borrowerId, setBorrowerId] = useState("");

  const { data: rows = [] } = useQuery({
    queryKey: ["library-reservations"],
    queryFn: () => listReservations(),
  });

  const create = useMutation({
    mutationFn: () =>
      createReservation({
        book_id: bookId!,
        borrower_kind: borrowerKind,
        borrower_id: Number(borrowerId),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-reservations"] });
      setBookId(null);
      setBorrowerId("");
    },
  });

  const cancel = useMutation({
    mutationFn: (id: number) => cancelReservation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-reservations"] }),
  });

  const canSubmit = bookId !== null && borrowerId.trim().length > 0 && !create.isPending;

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Reservations"
        subtitle="Queue borrowers for titles that are currently on loan. The reservation flips to 'ready' when a copy is returned."
      />

      <div className="grid gap-6 md:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Pick a title</CardTitle>
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
                    onClick={() => setBookId(b.id)}
                    className={cn(
                      "flex w-full flex-col rounded-md border px-3 py-2 text-left transition-colors",
                      bookId === b.id
                        ? "border-saffron bg-saffron-pale text-saffron-darker"
                        : "border-transparent hover:bg-muted",
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

        <Card>
          <CardHeader>
            <CardTitle>Reserve for a borrower</CardTitle>
            <CardDescription>
              {activeBook ? activeBook.title : "Pick a title on the left first."}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
                value={borrowerId}
                inputMode="numeric"
                      onChange={(e) => setBorrowerId(e.target.value.replace(/\D/g, ""))}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => create.mutate()} disabled={!canSubmit}>
                <Library className="mr-1 h-4 w-4" />
                Reserve
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reservation queue</CardTitle>
          <CardDescription>{rows.length} reservations</CardDescription>
        </CardHeader>
        <CardContent>
          {rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reservations.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Book</th>
                  <th>Borrower</th>
                  <th>Status</th>
                  <th>Requested</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-saffron-pale">
                    <td className="py-2">#{r.book_id}</td>
                    <td>
                      {r.borrower_kind} #{r.borrower_id}
                    </td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", RES_TONE[r.status])}>
                        {r.status}
                      </span>
                    </td>
                    <td>{new Date(r.requested_at).toLocaleString()}</td>
                    <td className="text-right">
                      {(r.status === "pending" || r.status === "ready") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => cancel.mutate(r.id)}
                        >
                          Cancel
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
