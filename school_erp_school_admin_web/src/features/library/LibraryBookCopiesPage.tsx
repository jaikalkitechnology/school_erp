import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { addCopiesBulk, listBooks, listCopies, type CopyStatus } from "./api";
import { LibraryHeader } from "./_shared";

const COPY_TONE: Record<CopyStatus, string> = {
  available: "bg-teal-pale text-teal-dark",
  issued: "bg-marigold-pale text-marigold-dark",
  reserved: "bg-saffron-pale text-saffron-darker",
  lost: "bg-destructive/15 text-destructive",
  damaged: "bg-destructive/15 text-destructive",
};

/** Manage physical copies of a book — pick a title, see every copy's
 * barcode + status, bulk-add more when the school buys extras. */
export function LibraryBookCopiesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [activeBook, setActiveBook] = useState<number | null>(null);

  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });
  const { data: copies = [], isLoading: copiesLoading } = useQuery({
    queryKey: ["library-copies", activeBook],
    queryFn: () => (activeBook ? listCopies(activeBook) : Promise.resolve([])),
    enabled: activeBook !== null,
  });

  const [copyCount, setCopyCount] = useState("1");
  const [barcodePrefix, setBarcodePrefix] = useState("");
  const addCopies = useMutation({
    mutationFn: () =>
      addCopiesBulk(activeBook!, {
        count: Number(copyCount) || 1,
        barcode_prefix: barcodePrefix || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-copies", activeBook] });
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setCopyCount("1");
      setBarcodePrefix("");
    },
  });

  const activeBookMeta = books.find((b) => b.id === activeBook);

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Book copies"
        subtitle="Physical copies of each title. Pick a book to see its copies, or bulk-add new ones when the school buys extras."
      />

      <div className="grid gap-6 md:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Titles</CardTitle>
            <CardDescription>{books.length} in catalogue</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Search title / ISBN"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="max-h-[520px] space-y-1 overflow-y-auto">
              {books.length === 0 ? (
                <p className="text-sm text-muted-foreground">No books yet.</p>
              ) : (
                books.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => setActiveBook(b.id)}
                    className={cn(
                      "flex w-full flex-col rounded-md border px-3 py-2 text-left transition-colors",
                      activeBook === b.id
                        ? "border-saffron bg-saffron-pale text-saffron-darker"
                        : "border-transparent hover:bg-muted",
                    )}
                  >
                    <span className="text-sm font-semibold">{b.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {b.available_copies} / {b.total_copies} available
                    </span>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {activeBook === null ? (
            <Card>
              <CardContent className="py-16 text-center text-sm text-muted-foreground">
                Pick a title on the left to view or add copies.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>
                    {activeBookMeta?.title ?? `Book #${activeBook}`}
                  </CardTitle>
                  <CardDescription>
                    {activeBookMeta && (
                      <>
                        {activeBookMeta.available_copies} of{" "}
                        {activeBookMeta.total_copies} copies available
                      </>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {copiesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading copies…</p>
                  ) : copies.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No copies yet. Add some below.
                    </p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <tr>
                          <th className="py-2">Copy #</th>
                          <th>Barcode</th>
                          <th>Accession</th>
                          <th>Status</th>
                          <th>Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {copies.map((c) => (
                          <tr key={c.id} className="border-t border-saffron-pale">
                            <td className="py-2">#{c.id}</td>
                            <td className="font-mono text-xs">{c.barcode}</td>
                            <td>{c.accession_number ?? "—"}</td>
                            <td>
                              <span
                                className={cn(
                                  "rounded px-2 py-0.5 text-xs",
                                  COPY_TONE[c.status],
                                )}
                              >
                                {c.status}
                              </span>
                            </td>
                            <td className="text-muted-foreground">
                              {c.notes ?? "—"}
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
                  <CardTitle>Add copies</CardTitle>
                  <CardDescription>
                    Barcodes auto-generated using the prefix (if any).
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <Label>How many?</Label>
                    <Input
                      value={copyCount}
                      onChange={(e) => setCopyCount(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Barcode prefix (optional)</Label>
                    <Input
                      value={barcodePrefix}
                      onChange={(e) => setBarcodePrefix(e.target.value)}
                      placeholder="LIB-2026-"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      onClick={() => addCopies.mutate()}
                      disabled={addCopies.isPending}
                    >
                      <Plus className="mr-1 h-4 w-4" />
                      Add copies
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
