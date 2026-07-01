import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reports } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Standalone circulation report. Same numbers the librarian sees
 * on the Dashboard, plus a category-wise breakdown table. */
export function LibraryReportsPage() {
  const { data } = useQuery({ queryKey: ["library-reports"], queryFn: reports });
  if (!data) {
    return (
      <div className="space-y-6">
        <LibraryHeader title="Reports" />
        <p className="text-sm text-muted-foreground">Loading circulation data…</p>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Reports"
        subtitle="Circulation snapshot. Numbers refresh whenever a book is issued, returned, or a fine is collected."
      />
      <div className="grid gap-4 md:grid-cols-5">
        <StatTile label="Books" value={data.total_books} />
        <StatTile label="Copies" value={data.total_copies} />
        <StatTile label="Issued" value={data.issued} tone="marigold" />
        <StatTile label="Overdue" value={data.overdue} tone="destructive" />
        <StatTile
          label="Fines outstanding"
          value={`₹${data.fines_outstanding}`}
          tone="saffron"
        />
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
