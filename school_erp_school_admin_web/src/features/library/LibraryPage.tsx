import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Hand, Library, Plus, RefreshCw, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  addCopiesBulk,
  cancelReservation,
  createBook,
  createReservation,
  issueLoan,
  listBooks,
  listLoans,
  listReservations,
  reports,
  returnLoan,
  sweepOverdue,
  type LoanStatus,
  type ReservationStatus,
} from "./api";

const TABS = ["Catalog", "Circulation", "Reservations", "Reports"] as const;
type Tab = (typeof TABS)[number];

const LOAN_TONE: Record<LoanStatus, string> = {
  active: "bg-marigold-pale text-marigold-dark",
  returned: "bg-teal-pale text-teal-dark",
  overdue: "bg-destructive/15 text-destructive",
  lost: "bg-destructive/15 text-destructive",
};

const RES_TONE: Record<ReservationStatus, string> = {
  pending: "bg-marigold-pale text-marigold-dark",
  ready: "bg-teal-pale text-teal-dark",
  fulfilled: "bg-muted text-muted-foreground",
  cancelled: "bg-muted text-muted-foreground",
};

export function LibraryPage() {
  const [tab, setTab] = useState<Tab>("Catalog");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 17 · Library
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Library</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Catalog books with multiple copies, issue + return at the desk, manage reservations,
          and watch fines pile up.
        </p>
      </header>
      <nav className="flex gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label
                ? "border-b-2 border-saffron text-saffron-darker"
                : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "Catalog" && <CatalogPanel />}
      {tab === "Circulation" && <CirculationPanel />}
      {tab === "Reservations" && <ReservationsPanel />}
      {tab === "Reports" && <ReportsPanel />}
    </div>
  );
}

// ---- Catalog -------------------------------------------------------------

function CatalogPanel() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });

  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isbn, setIsbn] = useState("");
  const [category, setCategory] = useState("");
  const [finePerDay, setFinePerDay] = useState("0");
  const [loanDays, setLoanDays] = useState("14");

  const create = useMutation({
    mutationFn: () =>
      createBook({
        title,
        author: author || undefined,
        isbn: isbn || undefined,
        category: category || undefined,
        default_fine_per_day: Number(finePerDay) || 0,
        default_loan_days: Number(loanDays) || 14,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setTitle("");
      setAuthor("");
      setIsbn("");
      setCategory("");
    },
  });

  const [activeBook, setActiveBook] = useState<number | null>(null);
  const addCopies = useMutation({
    mutationFn: (count: number) => addCopiesBulk(activeBook!, { count }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-books"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Books</CardTitle>
            <CardDescription>{books.length} titles in the catalog</CardDescription>
          </div>
          <Input
            placeholder="Search title / author / ISBN"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="max-w-xs"
          />
        </CardHeader>
        <CardContent>
          {books.length === 0 ? (
            <p className="text-sm text-muted-foreground">No books match.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Title</th>
                  <th>Author</th>
                  <th>Category</th>
                  <th>Avail / Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {books.map((b) => (
                  <tr key={b.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-medium text-indigo-dark">{b.title}</td>
                    <td>{b.author ?? "—"}</td>
                    <td>{b.category ?? "—"}</td>
                    <td>
                      <span className="rounded bg-teal-pale px-2 py-0.5 text-teal-dark">
                        {b.available_copies}
                      </span>
                      <span className="text-muted-foreground"> / {b.total_copies}</span>
                    </td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setActiveBook(b.id === activeBook ? null : b.id)}
                      >
                        {activeBook === b.id ? "Hide" : "Copies"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {activeBook && (
            <div className="mt-4 flex items-center gap-3 rounded border border-saffron-pale bg-saffron-pale/30 p-3">
              <span className="text-sm">Add</span>
              <Input
                type="number"
                min={1}
                max={50}
                defaultValue={5}
                className="w-20"
                id="copy-count"
              />
              <Button
                onClick={() => {
                  const el = document.getElementById("copy-count") as HTMLInputElement | null;
                  const n = Number(el?.value || "5");
                  addCopies.mutate(n);
                }}
                disabled={addCopies.isPending}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add copies
              </Button>
              <span className="text-xs text-muted-foreground">
                Barcodes auto-generated.
              </span>
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Add a book</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <Label>Author</Label>
            <Input value={author} onChange={(e) => setAuthor(e.target.value)} />
          </div>
          <div>
            <Label>ISBN</Label>
            <Input value={isbn} onChange={(e) => setIsbn(e.target.value)} />
          </div>
          <div>
            <Label>Category</Label>
            <Input value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Fine / day (₹)</Label>
              <Input value={finePerDay} onChange={(e) => setFinePerDay(e.target.value)} />
            </div>
            <div>
              <Label>Loan days</Label>
              <Input value={loanDays} onChange={(e) => setLoanDays(e.target.value)} />
            </div>
          </div>
          <Button onClick={() => create.mutate()} disabled={!title || create.isPending}>
            <BookOpen className="mr-1 h-4 w-4" />
            Save
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Circulation --------------------------------------------------------

function CirculationPanel() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<LoanStatus | "all">("active");
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", statusFilter],
    queryFn: () =>
      listLoans({ status_filter: statusFilter === "all" ? undefined : statusFilter }),
  });

  const [copyId, setCopyId] = useState("");
  const [borrowerId, setBorrowerId] = useState("");

  const issue = useMutation({
    mutationFn: () =>
      issueLoan({
        copy_id: Number(copyId),
        borrower_kind: "student",
        borrower_id: Number(borrowerId),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-loans"] });
      setCopyId("");
      setBorrowerId("");
    },
  });

  const sweep = useMutation({
    mutationFn: sweepOverdue,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  const ret = useMutation({
    mutationFn: (loanId: number) => returnLoan({ loan_id: loanId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-loans"] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Issue book</CardTitle>
          <CardDescription>Scan / type the copy barcode (use copy ID for now) and the student admission ID.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <div>
            <Label>Copy ID</Label>
            <Input value={copyId} onChange={(e) => setCopyId(e.target.value)} />
          </div>
          <div>
            <Label>Student ID</Label>
            <Input value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)} />
          </div>
          <div className="flex items-end">
            <Button onClick={() => issue.mutate()} disabled={!copyId || !borrowerId || issue.isPending}>
              <Hand className="mr-1 h-4 w-4" />
              Issue
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Loans</CardTitle>
            <CardDescription>{loans.length} {statusFilter} loans</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as LoanStatus | "all")}
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="returned">Returned</option>
              <option value="overdue">Overdue</option>
              <option value="lost">Lost</option>
            </select>
            <Button variant="outline" onClick={() => sweep.mutate()} disabled={sweep.isPending}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Sweep overdue
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loans.length === 0 ? (
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

// ---- Reservations -------------------------------------------------------

function ReservationsPanel() {
  const qc = useQueryClient();
  const { data: rows = [] } = useQuery({
    queryKey: ["library-reservations"],
    queryFn: () => listReservations(),
  });

  const [bookId, setBookId] = useState("");
  const [borrowerId, setBorrowerId] = useState("");

  const create = useMutation({
    mutationFn: () =>
      createReservation({
        book_id: Number(bookId),
        borrower_kind: "student",
        borrower_id: Number(borrowerId),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-reservations"] });
      setBookId("");
      setBorrowerId("");
    },
  });

  const cancel = useMutation({
    mutationFn: (id: number) => cancelReservation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-reservations"] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Place reservation</CardTitle>
          <CardDescription>Borrower will be auto-notified when a copy frees up.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <div>
            <Label>Book ID</Label>
            <Input value={bookId} onChange={(e) => setBookId(e.target.value)} />
          </div>
          <div>
            <Label>Student ID</Label>
            <Input value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)} />
          </div>
          <div className="flex items-end">
            <Button onClick={() => create.mutate()} disabled={!bookId || !borrowerId || create.isPending}>
              <Library className="mr-1 h-4 w-4" />
              Reserve
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Active reservations</CardTitle>
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
                    <td>{r.borrower_kind} #{r.borrower_id}</td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", RES_TONE[r.status])}>
                        {r.status}
                      </span>
                    </td>
                    <td>{new Date(r.requested_at).toLocaleString()}</td>
                    <td className="text-right">
                      {(r.status === "pending" || r.status === "ready") && (
                        <Button size="sm" variant="ghost" onClick={() => cancel.mutate(r.id)}>
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

// ---- Reports -------------------------------------------------------------

function ReportsPanel() {
  const { data } = useQuery({ queryKey: ["library-reports"], queryFn: reports });
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-5">
        <Tile label="Books" value={data.total_books} />
        <Tile label="Copies" value={data.total_copies} />
        <Tile label="Issued" value={data.issued} tone="marigold" />
        <Tile label="Overdue" value={data.overdue} tone="destructive" />
        <Tile label="Outstanding fines" value={`₹${data.fines_outstanding}`} tone="saffron" />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>By category</CardTitle>
        </CardHeader>
        <CardContent>
          {data.by_category.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Category</th>
                  <th>Books</th>
                  <th>Copies</th>
                </tr>
              </thead>
              <tbody>
                {data.by_category.map((c, i) => (
                  <tr key={i} className="border-t border-saffron-pale">
                    <td className="py-2">{c.category ?? "Uncategorised"}</td>
                    <td>{c.books}</td>
                    <td>{c.copies}</td>
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

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "marigold" | "destructive" | "saffron";
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 font-display text-2xl",
            tone === "marigold" && "text-marigold-dark",
            tone === "destructive" && "text-destructive",
            tone === "saffron" && "text-saffron-darker",
            !tone && "text-indigo-dark",
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
