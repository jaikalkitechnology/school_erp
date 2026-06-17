import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  bulkImportStudents,
  type BulkImportResult,
} from "./api";

const SAMPLE_CSV =
  "full_name,first_name,last_name,date_of_birth,gender,blood_group,admission_number,roll_no,class_def_id,section_id,address,phone,email,father_name,mother_name,parent_phone,parent_email\n" +
  "Asha Sharma,Asha,Sharma,2015-04-12,female,O+,,1,1,1,123 MG Road,,,Rakesh,Priya,9999999999,parent@example.com\n";

export function BulkImportDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<BulkImportResult | null>(null);

  const run = useMutation({
    mutationFn: () => bulkImportStudents(file!),
    onSuccess: (r) => {
      setResult(r);
      if (r.imported > 0) {
        qc.invalidateQueries({ queryKey: ["students"] });
      }
    },
  });

  const downloadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "students_template.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-background p-6 shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>
        <h2 className="font-display text-2xl text-indigo-dark">
          Bulk import students
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          CSV with a header row. <code className="font-mono">full_name</code> is
          required. <code className="font-mono">admission_number</code> auto-
          generates when blank. Re-upload only the failing rows after fixing
          them — successful rows aren't reverted.
        </p>
        <div className="mt-2">
          <Button variant="link" size="sm" onClick={downloadSample}>
            Download template
          </Button>
        </div>

        <div className="mt-4 rounded-md border border-dashed border-saffron-pale p-4">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
            }}
          />
          <div className="flex items-center justify-between">
            <p className="text-sm">
              {file ? (
                <>
                  <span className="font-medium text-indigo-dark">{file.name}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                </>
              ) : (
                <span className="text-muted-foreground">No file picked.</span>
              )}
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="h-4 w-4" />
              Pick CSV
            </Button>
          </div>
        </div>

        {result && (
          <div className="mt-4 space-y-2">
            <p className="text-sm">
              <span className="font-medium text-teal-dark">
                {result.imported} imported
              </span>
              {result.skipped > 0 && (
                <>
                  {" · "}
                  <span className="font-medium text-destructive">
                    {result.skipped} skipped
                  </span>
                </>
              )}
            </p>
            {result.errors.length > 0 && (
              <div className="max-h-56 overflow-y-auto rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground">
                      <th className="pb-1">Row</th>
                      <th className="pb-1">Name</th>
                      <th className="pb-1">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.errors.map((e) => (
                      <tr key={e.row} className="border-t border-destructive/15">
                        <td className="py-1 font-mono">{e.row}</td>
                        <td className="py-1">{e.full_name ?? "—"}</td>
                        <td className="py-1 text-destructive">{e.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {run.isError && (
          <p className="mt-3 text-sm text-destructive">
            {(run.error as any)?.response?.data?.detail ?? "Import failed"}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button
            disabled={!file || run.isPending}
            onClick={() => run.mutate()}
          >
            {run.isPending ? "Importing…" : "Import"}
          </Button>
        </div>
      </div>
    </div>
  );
}
