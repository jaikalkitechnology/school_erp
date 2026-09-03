import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { importBooks, listBooks, listLoans } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Minimal quote-aware CSV parser → array of row objects keyed by the
 * header row. Good enough for spreadsheets exported by Excel / Sheets. */
function parseCsv(text: string): Array<Record<string, string>> {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.some((f) => f !== "")) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); if (row.some((f) => f !== "")) rows.push(row); }
  if (rows.length < 2) return [];
  const header = rows[0].map((h) => h.trim().toLowerCase());
  return rows.slice(1).map((r) => {
    const obj: Record<string, string> = {};
    header.forEach((h, idx) => { obj[h] = (r[idx] ?? "").trim(); });
    return obj;
  });
}

/** Bulk data in / out. Export uses existing endpoints and builds
 * CSVs client-side; import is a preview-only stub until the
 * backend gets a bulk-ingest endpoint. */
export function LibraryImportExportPage() {
  const qc = useQueryClient();
  const { data: books = [] } = useQuery({
    queryKey: ["library-books"],
    queryFn: () => listBooks({}),
  });
  const { data: loans = [] } = useQuery({
    queryKey: ["library-loans", "all"],
    queryFn: () => listLoans({}),
  });

  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  const onImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileRef.current) fileRef.current.value = "";
    if (!file) return;
    setImporting(true);
    setImportMsg(null);
    try {
      const text = await file.text();
      const rows = parseCsv(text);
      if (rows.length === 0) {
        setImportMsg("No data rows found. Include a header row with a 'title' column.");
        return;
      }
      const res = await importBooks(rows);
      setImportMsg(`Imported ${res.created} book(s)${res.skipped ? `, skipped ${res.skipped}` : ""}.`);
      qc.invalidateQueries({ queryKey: ["library-books"] });
    } catch {
      setImportMsg("Import failed. Check the file is a valid CSV.");
    } finally {
      setImporting(false);
    }
  };

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
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={onImportFile}
          />
          <button
            type="button"
            disabled={importing}
            onClick={() => fileRef.current?.click()}
            className="flex w-full cursor-pointer items-center gap-3 rounded-md border border-dashed border-input bg-muted/40 px-4 py-6 text-left hover:bg-muted disabled:opacity-60"
          >
            <Upload className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm">
              {importing ? "Importing…" : "Click to choose a CSV of books to bulk-add."}
            </span>
          </button>
          {importMsg && <p className="text-sm text-teal-dark">{importMsg}</p>}
          <p className="text-xs text-muted-foreground">
            Expected columns (header row): <span className="font-mono">title, author, isbn, publisher, category</span>. Only <span className="font-mono">title</span> is required.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
