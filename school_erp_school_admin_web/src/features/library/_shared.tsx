import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import type { LoanStatus, ReservationStatus } from "./api";

export const LOAN_TONE: Record<LoanStatus, string> = {
  active: "bg-marigold-pale text-marigold-dark",
  returned: "bg-teal-pale text-teal-dark",
  overdue: "bg-destructive/15 text-destructive",
  lost: "bg-destructive/15 text-destructive",
};

export const RES_TONE: Record<ReservationStatus, string> = {
  pending: "bg-marigold-pale text-marigold-dark",
  ready: "bg-teal-pale text-teal-dark",
  fulfilled: "bg-muted text-muted-foreground",
  cancelled: "bg-muted text-muted-foreground",
};

/** Big stat tile used across the Dashboard and Reports pages. */
export function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "marigold" | "destructive" | "saffron" | "teal";
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 font-display text-2xl",
            tone === "marigold" && "text-marigold-dark",
            tone === "destructive" && "text-destructive",
            tone === "saffron" && "text-saffron-darker",
            tone === "teal" && "text-teal-dark",
            !tone && "text-indigo-dark",
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

/** Sticky page header used on every Library sub-page. */
export function LibraryHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header>
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
        Library
      </p>
      <h1 className="mt-1 font-display text-4xl text-indigo-dark">{title}</h1>
      {subtitle && (
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">{subtitle}</p>
      )}
    </header>
  );
}
