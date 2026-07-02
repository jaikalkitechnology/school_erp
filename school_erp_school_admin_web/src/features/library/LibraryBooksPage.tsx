import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createBook, deleteBook, listBooks, updateBook, type Book } from "./api";
import { LibraryHeader } from "./_shared";

/** Full CRUD on the catalogue — Create (form at bottom), Read
 * (searchable table), Update (edit modal), Delete (with a confirm).
 * Copies are managed separately on the Book Copies tab. */
export function LibraryBooksPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });

  // ---- Create ------------------------------------------------------
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

  // ---- Update / Delete --------------------------------------------
  const [editing, setEditing] = useState<Book | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Book | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const del = useMutation({
    mutationFn: (id: number) => deleteBook(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setConfirmDelete(null);
      setDeleteError(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setDeleteError(
        typeof detail === "string"
          ? detail
          : "Could not delete this book. Try again.",
      );
    },
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Books"
        subtitle="The catalogue. Create, edit, or remove titles here; copies live on the Book Copies tab."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Books</CardTitle>
            <CardDescription>{books.length} titles in the catalog</CardDescription>
          </div>
          <div className="w-64">
            <Input placeholder="Search title / ISBN" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </CardHeader>
        <CardContent>
          {books.length === 0 ? (
            <p className="text-sm text-muted-foreground">No books yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Title</th>
                  <th>Author</th>
                  <th>ISBN</th>
                  <th>Category</th>
                  <th>Copies (avail / total)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {books.map((b) => (
                  <tr key={b.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-medium text-indigo-dark">{b.title}</td>
                    <td>{b.author ?? "—"}</td>
                    <td className="font-mono text-xs">{b.isbn ?? "—"}</td>
                    <td>{b.category ?? "—"}</td>
                    <td>
                      {b.available_copies} / {b.total_copies}
                    </td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditing(b)}
                      >
                        <Pencil className="mr-1 h-3 w-3" />
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => {
                          setConfirmDelete(b);
                          setDeleteError(null);
                        }}
                      >
                        <Trash2 className="mr-1 h-3 w-3" />
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Add a book</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Title *</Label>
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
            <div>
              <Label>Fine / day (₹)</Label>
              <Input value={finePerDay} onChange={(e) => setFinePerDay(e.target.value)} />
            </div>
            <div>
              <Label>Default loan (days)</Label>
              <Input value={loanDays} onChange={(e) => setLoanDays(e.target.value)} />
            </div>
          </div>
          <Button onClick={() => create.mutate()} disabled={!title || create.isPending}>
            <BookOpen className="mr-1 h-4 w-4" />
            Save book
          </Button>
        </CardContent>
      </Card>

      {editing && (
        <EditBookDialog
          book={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["library-books"] });
            setEditing(null);
          }}
        />
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={`Delete "${confirmDelete.title}"?`}
          body={
            <>
              This removes the title and every copy of it. Copies currently on
              loan will block the delete — return them first.
            </>
          }
          confirmLabel="Delete book"
          error={deleteError}
          busy={del.isPending}
          onCancel={() => {
            setConfirmDelete(null);
            setDeleteError(null);
          }}
          onConfirm={() => del.mutate(confirmDelete.id)}
        />
      )}
    </div>
  );
}

// ---- Edit dialog ---------------------------------------------------------

function EditBookDialog({
  book,
  onClose,
  onSaved,
}: {
  book: Book;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(book.title);
  const [author, setAuthor] = useState(book.author ?? "");
  const [isbn, setIsbn] = useState(book.isbn ?? "");
  const [category, setCategory] = useState(book.category ?? "");
  const [finePerDay, setFinePerDay] = useState(String(book.default_fine_per_day ?? 0));
  const [loanDays, setLoanDays] = useState(String(book.default_loan_days ?? 14));
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      updateBook(book.id, {
        title,
        author: author || undefined,
        isbn: isbn || undefined,
        category: category || undefined,
        default_fine_per_day: Number(finePerDay) || 0,
        default_loan_days: Number(loanDays) || 14,
      }),
    onSuccess: onSaved,
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(
        typeof detail === "string" ? detail : "Could not save changes.",
      );
    },
  });

  return (
    <ModalShell onClose={onClose} title="Edit book" subtitle={`#${book.id}`}>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Title *</Label>
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
        <div>
          <Label>Fine / day (₹)</Label>
          <Input value={finePerDay} onChange={(e) => setFinePerDay(e.target.value)} />
        </div>
        <div>
          <Label>Default loan (days)</Label>
          <Input value={loanDays} onChange={(e) => setLoanDays(e.target.value)} />
        </div>
      </div>
      {errorMsg && (
        <p className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errorMsg}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={() => {
            setErrorMsg(null);
            save.mutate();
          }}
          disabled={!title || save.isPending}
        >
          Save changes
        </Button>
      </div>
    </ModalShell>
  );
}

// ---- Confirm dialog + modal shell ---------------------------------------

function ConfirmDialog({
  title,
  body,
  confirmLabel,
  error,
  busy,
  onCancel,
  onConfirm,
}: {
  title: string;
  body: React.ReactNode;
  confirmLabel: string;
  error: string | null;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <ModalShell onClose={onCancel} title={title}>
      <p className="text-sm text-muted-foreground">{body}</p>
      {error && (
        <p className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          disabled={busy}
          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
        >
          {confirmLabel}
        </Button>
      </div>
    </ModalShell>
  );
}

function ModalShell({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-saffron-pale bg-warm-white p-6 shadow-lg">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="font-display text-xl text-indigo-dark">{title}</h2>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
