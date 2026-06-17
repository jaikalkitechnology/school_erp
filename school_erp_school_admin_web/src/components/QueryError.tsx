import type { UseQueryResult } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";

/** Standardised error renderer for useQuery() failures.
 *
 *  Lots of admin pages were silently stuck on "Loading…" when the
 *  backend returned 4xx/5xx — useQuery just stopped, and the UI kept
 *  the spinner. This component reads the axios error's response body
 *  (where FastAPI puts `{ detail: "..." }`) and shows it inline. Use
 *  like: `if (q.isError) return <QueryError q={q} label="students" />;` */
export function QueryError({
  q,
  label,
  className,
}: {
  q: Pick<UseQueryResult, "error" | "refetch">;
  label?: string;
  className?: string;
}) {
  const e = q.error as any;
  const status = e?.response?.status;
  const detail =
    e?.response?.data?.detail ??
    e?.response?.data?.message ??
    e?.message ??
    "Unknown error";

  return (
    <div
      className={
        "flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm " +
        (className ?? "")
      }
    >
      <div className="flex items-center gap-2 text-destructive">
        <AlertCircle className="h-4 w-4" />
        <span className="font-medium">
          Could not load {label ?? "data"}
          {status ? ` (HTTP ${status})` : ""}
        </span>
      </div>
      <p className="text-xs text-destructive/80">{detail}</p>
      <button
        type="button"
        onClick={() => q.refetch()}
        className="text-xs text-destructive underline hover:no-underline"
      >
        Retry
      </button>
    </div>
  );
}
