import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reports } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Landing page for the librarian. Shows top-line counts (books,
 * copies, issued, overdue, outstanding fines) plus a category
 * breakdown. Navigation to Books / Categories / Issue / Return /
 * Fines / Reports lives in the left sidebar. */
export function LibraryDashboardPage() {
  const { data } = useQuery({ queryKey: ["library-reports"], queryFn: reports });
  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Library dashboard"
        subtitle="Circulation at a glance. Use the sidebar to jump into Books, Categories, Copies, Issue, Return, Fines, or Reports."
      />
      {data && (
        <div className="grid gap-4 md:grid-cols-5">
          <StatTile label="Books" value={data.total_books} />
          <StatTile label="Copies" value={data.total_copies} />
          <StatTile label="Issued" value={data.issued} tone="marigold" />
          <StatTile label="Overdue" value={data.overdue} tone="destructive" />
          <StatTile label="Fines due" value={`₹${data.fines_outstanding}`} tone="saffron" />
        </div>
      )}
      {data && (
        <Card>
          <CardHeader>
            <CardTitle>By category</CardTitle>
          </CardHeader>
          <CardContent>
            {data.by_category.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No categories yet. Add one when you save a book on the Books
                tab.
              </p>
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
      )}
    </div>
  );
}
