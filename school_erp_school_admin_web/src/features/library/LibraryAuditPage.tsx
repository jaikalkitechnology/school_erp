import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookPlus, BoxSelect, Hand, RotateCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { recentActivity, type ActivityEvent } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

const KIND_META: Record<
  ActivityEvent["kind"],
  { label: string; icon: React.ReactNode; tone: string }
> = {
  issue: {
    label: "Book issued",
    icon: <Hand className="h-4 w-4" />,
    tone: "bg-marigold-pale text-marigold-dark",
  },
  return: {
    label: "Book returned",
    icon: <RotateCcw className="h-4 w-4" />,
    tone: "bg-teal-pale text-teal-dark",
  },
  book_created: {
    label: "Title added",
    icon: <BookPlus className="h-4 w-4" />,
    tone: "bg-saffron-pale text-saffron-darker",
  },
  copy_created: {
    label: "Copy added",
    icon: <BoxSelect className="h-4 w-4" />,
    tone: "bg-saffron-pale text-saffron-darker",
  },
};

/** Recent-activity feed for the library. Without a dedicated audit
 * log table, we synthesise this from the created_at columns on
 * loans / books / copies + returned_on on loans. Ordered
 * chronologically, filterable by event kind. */
export function LibraryAuditPage() {
  const [kindFilter, setKindFilter] = useState<ActivityEvent["kind"] | "all">("all");
  const [q, setQ] = useState("");
  const { data: events = [], isLoading } = useQuery({
    queryKey: ["library-activity"],
    queryFn: () => recentActivity(150),
  });

  const filtered = useMemo(() => {
    const base = kindFilter === "all" ? events : events.filter((e) => e.kind === kindFilter);
    if (!q.trim()) return base;
    const needle = q.trim().toLowerCase();
    return base.filter((e) => JSON.stringify(e).toLowerCase().includes(needle));
  }, [events, kindFilter, q]);

  const counts = useMemo(() => {
    const c: Record<ActivityEvent["kind"], number> = {
      issue: 0,
      return: 0,
      book_created: 0,
      copy_created: 0,
    };
    for (const e of events) c[e.kind]++;
    return c;
  }, [events]);

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Audit logs"
        subtitle="Chronological feed of the last 150 library actions. Synthesised from the loans, books, and copies tables until a dedicated audit table lands."
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatTile label="Issues" value={counts.issue} tone="marigold" />
        <StatTile label="Returns" value={counts.return} tone="teal" />
        <StatTile label="Titles added" value={counts.book_created} tone="saffron" />
        <StatTile label="Copies added" value={counts.copy_created} tone="saffron" />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Activity</CardTitle>
            <CardDescription>
              {isLoading ? "Loading…" : `${filtered.length} events`}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Input
              className="w-56"
              placeholder="Filter (title / borrower / barcode)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={kindFilter}
              onChange={(e) => setKindFilter(e.target.value as typeof kindFilter)}
            >
              <option value="all">All events</option>
              <option value="issue">Issues</option>
              <option value="return">Returns</option>
              <option value="book_created">Titles added</option>
              <option value="copy_created">Copies added</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 && !isLoading ? (
            <p className="text-sm text-muted-foreground">No events match.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {filtered.map((e, i) => {
                const meta = KIND_META[e.kind];
                return (
                  <li key={i} className="flex items-start gap-3 py-3 text-sm">
                    <span
                      className={`mt-0.5 flex h-8 w-8 items-center justify-center rounded-full ${meta.tone}`}
                    >
                      {meta.icon}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium text-indigo-dark">{meta.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {describe(e)}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {e.when ? new Date(e.when).toLocaleString() : "—"}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function describe(e: ActivityEvent): string {
  switch (e.kind) {
    case "issue":
      return `Loan #${e.loan_id} · Copy #${e.copy_id} → ${e.borrower_kind} #${e.borrower_id}`;
    case "return":
      return `Loan #${e.loan_id} · Copy #${e.copy_id} · Fine paid ₹${e.fine_paid ?? 0}`;
    case "book_created":
      return `Title #${e.book_id} — ${e.title ?? ""}`;
    case "copy_created":
      return `Copy #${e.copy_id} · Book #${e.book_id} · ${e.barcode ?? ""}`;
  }
}
