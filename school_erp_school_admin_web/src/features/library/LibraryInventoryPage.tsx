import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, ScanLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listBooks, listCopies } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Session-based inventory check. Pick a book, tick each copy as
 * you spot it on the shelf. The count of unverified copies at the
 * end is the missing-copies report for that title. State is held
 * in-memory so refreshing loses progress — good enough for a
 * per-title walk-through; server-side sessions come later. */
export function LibraryInventoryPage() {
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

  const [verified, setVerified] = useState<Record<number, boolean>>({});
  const [scan, setScan] = useState("");

  // Auto-tick when a barcode is scanned into the input.
  const handleScan = () => {
    const match = copies.find((c) => c.barcode === scan.trim());
    if (match) {
      setVerified((v) => ({ ...v, [match.id]: true }));
      setScan("");
    }
  };

  const counts = useMemo(() => {
    const total = copies.length;
    const seen = copies.filter((c) => verified[c.id]).length;
    return { total, seen, missing: total - seen };
  }, [copies, verified]);

  const active = books.find((b) => b.id === bookId);

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Inventory verification"
        subtitle="Walk the shelf. Tick each copy as you spot it — or scan the barcode straight into the input below. Missing copies stay unticked."
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
              {books.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => {
                    setBookId(b.id);
                    setVerified({});
                  }}
                  className={cn(
                    "flex w-full flex-col rounded-md border px-3 py-2 text-left transition-colors",
                    bookId === b.id
                      ? "border-saffron bg-saffron-pale text-saffron-darker"
                      : "border-transparent hover:bg-muted",
                  )}
                >
                  <span className="text-sm font-semibold">{b.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {b.total_copies} copies on record
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {active === undefined ? (
            <Card>
              <CardContent className="py-16 text-center text-sm text-muted-foreground">
                Pick a title on the left to start a walk-through.
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <StatTile label="On record" value={counts.total} />
                <StatTile label="Verified" value={counts.seen} tone="teal" />
                <StatTile
                  label="Missing"
                  value={counts.missing}
                  tone={counts.missing > 0 ? "destructive" : "teal"}
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Scan or tap</CardTitle>
                  <CardDescription>{active.title}</CardDescription>
                </CardHeader>
                <CardContent>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleScan();
                    }}
                    className="mb-4 flex items-center gap-2"
                  >
                    <ScanLine className="h-4 w-4 text-muted-foreground" />
                    <Input
                      autoFocus
                      value={scan}
                      onChange={(e) => setScan(e.target.value)}
                      placeholder="Scan or paste a barcode…"
                    />
                    <Button type="submit" disabled={!scan.trim()}>
                      Tick
                    </Button>
                  </form>

                  {copies.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No copies on record for this title.
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                      {copies.map((c) => {
                        const seen = !!verified[c.id];
                        return (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() =>
                              setVerified((v) => ({ ...v, [c.id]: !v[c.id] }))
                            }
                            className={cn(
                              "flex items-center gap-2 rounded-md border px-3 py-2 text-left text-xs transition-colors",
                              seen
                                ? "border-teal-dark bg-teal-pale text-teal-dark"
                                : "border-input hover:bg-muted",
                            )}
                          >
                            {seen ? (
                              <CheckCircle2 className="h-4 w-4" />
                            ) : (
                              <Circle className="h-4 w-4 text-muted-foreground" />
                            )}
                            <span className="font-mono">{c.barcode}</span>
                            <span className="ml-auto text-muted-foreground">
                              {c.status}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
