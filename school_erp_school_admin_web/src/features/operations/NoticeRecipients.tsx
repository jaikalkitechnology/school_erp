import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Person {
  user_id: number;
  name: string;
  detail: string;
}

const NOUN: Record<string, string> = { staff: "staff", parents: "parents", students: "students" };

const fetchPeople = async (audience: string) =>
  (await api.get<Person[]>("/v1/operations/notices/recipients", { params: { audience } })).data;

/** The value is "" for everyone in the audience, or a JSON list of user ids. */
export const parseIds = (value: string): number[] => {
  if (!value) return [];
  try {
    const v = JSON.parse(value);
    return Array.isArray(v) ? v.filter((x) => typeof x === "number") : [];
  } catch {
    return [];
  }
};

/** "Send to" for a notice: everyone in the chosen audience, or particular
 *  people picked from a searchable list. */
export function NoticeRecipients({
  audience,
  value,
  onChange,
  invalid,
}: {
  audience: string;
  value: string;
  onChange: (v: string) => void;
  invalid: boolean;
}) {
  const noun = NOUN[audience];
  const particular = value !== "";
  const ids = useMemo(() => parseIds(value), [value]);
  const [query, setQuery] = useState("");

  const people = useQuery({
    queryKey: ["notice-recipients", audience],
    queryFn: () => fetchPeople(audience),
    enabled: Boolean(noun) && particular,
    staleTime: 60_000,
  });

  if (!noun) {
    return <p className="mt-1 text-sm text-muted-foreground">Everyone in the school sees this notice.</p>;
  }

  const byId = new Map((people.data ?? []).map((p) => [p.user_id, p]));
  const q = query.trim().toLowerCase();
  const shown = (people.data ?? []).filter(
    (p) => !q || p.name.toLowerCase().includes(q) || p.detail.toLowerCase().includes(q),
  );
  const set = (next: number[]) => onChange(JSON.stringify([...new Set(next)]));
  const toggle = (id: number) => set(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  return (
    <div className="mt-1 space-y-2">
      <div className="flex flex-wrap gap-4 text-sm" role="radiogroup" aria-label="Send to">
        <label className="flex items-center gap-2">
          <input type="radio" className="accent-saffron" checked={!particular} onChange={() => onChange("")} />
          All {noun}
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" className="accent-saffron" checked={particular} onChange={() => onChange("[]")} />
          Particular {noun}
        </label>
      </div>

      {particular && (
        <div className={cn("rounded-md border bg-background", invalid ? "border-destructive" : "border-input")}>
          {ids.length > 0 && (
            <div className="flex flex-wrap gap-1.5 border-b border-input p-2">
              {ids.map((id) => (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 rounded-full bg-saffron-pale px-2.5 py-0.5 text-xs font-medium text-saffron-darker"
                >
                  {byId.get(id)?.name ?? `User #${id}`}
                  <button
                    type="button"
                    onClick={() => toggle(id)}
                    aria-label={`Remove ${byId.get(id)?.name ?? id}`}
                    className="rounded-full hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="relative border-b border-input">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${noun} by name${audience === "students" ? ", class or admission no." : audience === "parents" ? " or child" : " or role"}`}
              className="h-9 w-full bg-transparent pl-8 pr-2 text-sm outline-none"
              aria-label={`Search ${noun}`}
            />
          </div>
          <div className="max-h-56 overflow-y-auto">
            {people.isLoading ? (
              <p className="px-3 py-3 text-sm text-muted-foreground">Loading {noun}…</p>
            ) : people.isError ? (
              <p className="px-3 py-3 text-sm text-destructive">Couldn't load {noun}.</p>
            ) : shown.length === 0 ? (
              <p className="px-3 py-3 text-sm text-muted-foreground">
                {(people.data ?? []).length === 0 ? `No ${noun} with an app login yet.` : "No matches."}
              </p>
            ) : (
              <ul>
                {shown.map((p) => (
                  <li key={p.user_id}>
                    <label className="flex cursor-pointer items-start gap-2.5 px-3 py-2 text-sm hover:bg-saffron-pale/40">
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 accent-saffron"
                        checked={ids.includes(p.user_id)}
                        onChange={() => toggle(p.user_id)}
                      />
                      <span className="min-w-0">
                        <span className="block font-medium text-indigo-dark">{p.name}</span>
                        {p.detail && <span className="block text-xs text-muted-foreground">{p.detail}</span>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex items-center justify-between border-t border-input px-3 py-1.5 text-xs text-muted-foreground">
            <span>{ids.length} selected</span>
            <span className="flex gap-3">
              <button
                type="button"
                className="font-semibold text-saffron-darker hover:underline disabled:opacity-40"
                disabled={shown.length === 0}
                onClick={() => set([...ids, ...shown.map((p) => p.user_id)])}
              >
                Select all shown
              </button>
              <button
                type="button"
                className="font-semibold hover:underline disabled:opacity-40"
                disabled={ids.length === 0}
                onClick={() => onChange("[]")}
              >
                Clear
              </button>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
