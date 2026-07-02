import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { listBooks, listCopies, type CopyStatus } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

const COPY_TONE: Record<CopyStatus, string> = {
  available: "bg-teal-pale text-teal-dark",
  issued: "bg-marigold-pale text-marigold-dark",
  reserved: "bg-saffron-pale text-saffron-darker",
  lost: "bg-destructive/15 text-destructive",
  damaged: "bg-destructive/15 text-destructive",
};

/** Lost & Damaged register — shows every copy currently in the
 * ``lost`` or ``damaged`` state so the librarian can chase
 * replacements. Fed by the same book / copy tables as everywhere
 * else. Marking a copy lost is done via the Return endpoint's
 * ``mark_lost`` flag; the surface for that lives on Return Books. */
export function LibraryLostDamagedPage() {
  const [q, setQ] = useState("");
  const { data: books = [] } = useQuery({
    queryKey: ["library-books"],
    queryFn: () => listBooks({}),
  });

  // Pull every book's copies. This is O(N books) requests — fine
  // for a school library with hundreds of titles, not thousands.
  // A dedicated /copies?status=lost endpoint would be an easy add
  // when we grow past that.
  const copyQueries = useQuery({
    queryKey: ["library-copies-all", books.map((b) => b.id)],
    queryFn: async () => {
      const out: {
        copy: Awaited<ReturnType<typeof listCopies>>[number];
        book: (typeof books)[number];
      }[] = [];
      for (const b of books) {
        const copies = await listCopies(b.id);
        for (const c of copies) {
          if (c.status === "lost" || c.status === "damaged") {
            out.push({ copy: c, book: b });
          }
        }
      }
      return out;
    },
    enabled: books.length > 0,
  });

  const rows = copyQueries.data ?? [];

  const filtered = useMemo(() => {
    if (!q.trim()) return rows;
    const needle = q.trim().toLowerCase();
    return rows.filter(
      (r) =>
        r.book.title.toLowerCase().includes(needle) ||
        r.copy.barcode.toLowerCase().includes(needle) ||
        (r.copy.accession_number ?? "").toLowerCase().includes(needle),
    );
  }, [rows, q]);

  const counts = useMemo(() => {
    const lost = rows.filter((r) => r.copy.status === "lost").length;
    const damaged = rows.filter((r) => r.copy.status === "damaged").length;
    return { lost, damaged, total: rows.length };
  }, [rows]);

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Lost & damaged books"
        subtitle="Register of every copy currently marked lost or damaged. Mark a loan as lost from the Return Books page."
      />
      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label="Lost copies" value={counts.lost} tone="destructive" />
        <StatTile label="Damaged copies" value={counts.damaged} tone="destructive" />
        <StatTile label="Total out of circulation" value={counts.total} tone="saffron" />
      </div>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Register</CardTitle>
            <CardDescription>
              {copyQueries.isLoading
                ? "Scanning copies…"
                : `${filtered.length} copies`}
            </CardDescription>
          </div>
          <div className="w-64">
            <Input
              placeholder="Filter by title / barcode / accession"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {rows.length === 0 && !copyQueries.isLoading ? (
            <p className="text-sm text-muted-foreground">
              Nothing in the lost or damaged register. Nice.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Title</th>
                  <th>Barcode</th>
                  <th>Accession</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(({ copy, book }) => (
                  <tr key={copy.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-medium text-indigo-dark">
                      {book.title}
                    </td>
                    <td className="font-mono text-xs">{copy.barcode}</td>
                    <td>{copy.accession_number ?? "—"}</td>
                    <td>
                      <span
                        className={cn(
                          "rounded px-2 py-0.5 text-xs",
                          COPY_TONE[copy.status],
                        )}
                      >
                        {copy.status}
                      </span>
                    </td>
                    <td className="text-muted-foreground">{copy.notes ?? "—"}</td>
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
