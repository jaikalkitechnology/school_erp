import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listBooks, listCopies } from "./api";
import { LibraryHeader } from "./_shared";

/** Barcode label preview + print. Pick a title, see printable
 * labels for every copy, click Print (opens the browser print
 * dialog with just the labels visible). No external barcode font —
 * we render the barcode value monospace inside a bordered box,
 * good enough for schools using a generic label printer. Swap in a
 * proper Code-128 svg later. */
export function LibraryBarcodePage() {
  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books", q],
    queryFn: () => listBooks({ q: q || undefined }),
  });
  const [bookId, setBookId] = useState<number | null>(null);

  const { data: copies = [] } = useQuery({
    queryKey: ["library-copies", bookId],
    queryFn: () => (bookId ? listCopies(bookId) : Promise.resolve([])),
    enabled: bookId !== null,
  });

  const active = books.find((b) => b.id === bookId);
  const printable = useMemo(() => copies.slice().sort((a, b) => a.id - b.id), [copies]);

  const doPrint = () => window.print();

  return (
    <div className="space-y-6 print:space-y-2">
      <div className="print:hidden">
        <LibraryHeader
          title="Barcode management"
          subtitle="Preview and print barcode stickers for every copy of a title. Uses the browser's print dialog — set page size to your label sheet before printing."
        />
      </div>

      <div className="grid gap-6 md:grid-cols-[320px_1fr] print:grid-cols-1">
        <Card className="print:hidden">
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
              {books.map((b) => (
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
                    {b.total_copies} copies
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {active === undefined ? (
            <Card className="print:hidden">
              <CardContent className="py-16 text-center text-sm text-muted-foreground">
                Pick a title on the left to preview its labels.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card className="print:hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <div>
                    <CardTitle>{active.title}</CardTitle>
                    <CardDescription>
                      {printable.length} labels · use browser print (Ctrl/Cmd+P)
                    </CardDescription>
                  </div>
                  <Button onClick={doPrint}>
                    <Printer className="mr-1 h-4 w-4" /> Print labels
                  </Button>
                </CardHeader>
              </Card>

              <div
                className={cn(
                  "grid grid-cols-2 gap-3 md:grid-cols-3",
                  "print:grid-cols-3 print:gap-2",
                )}
              >
                {printable.map((c) => (
                  <div
                    key={c.id}
                    className="rounded border border-input bg-white p-3 text-center shadow-sm print:border-black print:shadow-none"
                  >
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground print:text-black">
                      {active.title.slice(0, 30)}
                    </p>
                    <div
                      className="my-2 border-y border-black py-2 font-mono text-lg font-bold tracking-[0.35em] text-black"
                      style={{ fontFamily: "Menlo, Consolas, monospace" }}
                    >
                      {c.barcode}
                    </div>
                    <p className="text-[10px] text-muted-foreground print:text-black">
                      #{c.id}
                      {c.accession_number ? ` · ${c.accession_number}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
