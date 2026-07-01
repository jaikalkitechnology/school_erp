import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { reports } from "./api";
import { LibraryHeader } from "./_shared";

/** Categories are free-text strings on Book.category. We surface the
 * distinct set via /library/reports.by_category — that's the source
 * of truth. Adding a category = adding a book with that string. */
export function LibraryCategoriesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["library-reports"],
    queryFn: () => import("./api").then((m) => m.reports()),
  });

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Categories"
        subtitle="Shows every category currently in use. Add a new one by typing it into the Category field when creating a book."
      />
      <Card>
        <CardHeader>
          <CardTitle>Category breakdown</CardTitle>
          <CardDescription>
            {data ? `${data.by_category.length} categories in use` : "Loading…"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !data || data.by_category.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No categories yet. Add one when you save a book on the Books tab.
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
                    <td className="py-2 font-medium text-indigo-dark">
                      {c.category ?? "Uncategorised"}
                    </td>
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
