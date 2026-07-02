import { useQuery } from "@tanstack/react-query";
import { Download, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listBooks, listLoans } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Bulk data in / out. Export uses existing endpoints and builds
 * CSVs client-side; import is a preview-only stub until the
 * backend gets a bulk-ingest endpoint. */
export function LibraryImportExportPage() {
  const { data: books = [] } = useQuery({
    queryKey: ["library-books"],
    queryFn: () => listBooks({}),
  });
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "all"],
    queryFn: () => listLoans({}),
  });

  const downloadCsv = (name: string, rows: string[][]) => {
    const csv = rows
      .map((r) =>
        r
          .map((cell) => {
            const s = String(cell ?? "");
            if (/["\n,]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
            return s;
          })
          .join(","),
      )
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const exportBooks = () =>
    downloadCsv("library-books.csv", [
      ["id", "title", "author", "isbn", "publisher", "category", "language", "default_loan_days", "default_fine_per_day", "total_copies", "available_copies"],
      ...books.map((b) => [
        String(b.id),
        b.title,
        b.author ?? "",
        b.isbn ?? "",
        b.publisher ?? "",
        b.category ?? "",
        b.language ?? "",
        String(b.default_loan_days),
        String(b.default_fine_per_day),
        String(b.total_copies),
        String(b.available_copies),
      ]),
    ]);

  const exportLoans = () =>
    downloadCsv("library-loans.csv", [
      ["loan_id", "copy_id", "book_id", "borrower_kind", "borrower_id", "issued_on", "due_on", "returned_on", "status", "fine_amount", "fine_paid"],
      ...loans.map((l) => [
        String(l.id),
        String(l.copy_id),
        String(l.book_id),
        l.borrower_kind,
        String(l.borrower_id),
        l.issued_on,
        l.due_on,
        l.returned_on ?? "",
        l.status,
        String(l.fine_amount),
        String(l.fine_paid),
      ]),
    ]);

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Import / export"
        subtitle="Move data in and out of the library. Exports run in your browser and download as CSV; imports are queued for backend support."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label="Books to export" value={books.length} />
        <StatTile label="Loans on record" value={loans.length} tone="marigold" />
        <StatTile label="Formats" value="CSV" tone="teal" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Export</CardTitle>
          <CardDescription>
            Downloads a CSV file with the current data. Open in Excel or
            Google Sheets.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button onClick={exportBooks} disabled={books.length === 0}>
            <Download className="mr-1 h-4 w-4" /> Export books ({books.length})
          </Button>
          <Button onClick={exportLoans} disabled={loans.length === 0}>
            <Download className="mr-1 h-4 w-4" /> Export loans ({loans.length})
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Import</CardTitle>
          <CardDescription>
            Upload a CSV of books to bulk-add. The importer validates each
            row, previews the changes, and only commits when you confirm.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="flex cursor-not-allowed items-center gap-3 rounded-md border border-dashed border-input bg-muted/40 px-4 py-6 opacity-70">
            <Upload className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm">
              Drop a CSV here or click to browse — <em>backend endpoint coming next</em>.
            </span>
          </label>
          <p className="text-xs text-muted-foreground">
            Expected columns: <span className="font-mono">title, author, isbn, publisher, category, default_loan_days, default_fine_per_day, copies</span>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
