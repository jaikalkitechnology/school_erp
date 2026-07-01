import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { addCopiesBulk, createBook, listBooks } from "./api";
import { LibraryHeader } from "./_shared";

/** Catalogue management: search titles, add a new title, bulk-add
 * copies to a title. */
export function LibraryBooksPage() {
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
  const [copyCount, setCopyCount] = useState("1");
  const addCopies = useMutation({
    mutationFn: () => addCopiesBulk(activeBook!, { count: Number(copyCount) || 1 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setCopyCount("1");
    },
  });

  return (
    <div className="space-y-6">
      <LibraryHeader title="Books" subtitle="The catalogue. Search titles, add new books, drop in extra copies." />

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
                    <td>{b.category ?? "—"}</td>
                    <td>
                      {b.available_copies} / {b.total_copies}
                    </td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant={activeBook === b.id ? "default" : "ghost"}
                        onClick={() => setActiveBook(activeBook === b.id ? null : b.id)}
                      >
                        <Plus className="mr-1 h-3 w-3" />
                        Copies
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {activeBook !== null && (
        <Card>
          <CardHeader>
            <CardTitle>Add copies to book #{activeBook}</CardTitle>
            <CardDescription>Barcodes are auto-generated per copy.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-end gap-3">
            <div className="w-40">
              <Label>How many?</Label>
              <Input value={copyCount} onChange={(e) => setCopyCount(e.target.value)} />
            </div>
            <Button onClick={() => addCopies.mutate()} disabled={addCopies.isPending}>
              <Plus className="mr-1 h-4 w-4" />
              Add copies
            </Button>
          </CardContent>
        </Card>
      )}

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
    </div>
  );
}
