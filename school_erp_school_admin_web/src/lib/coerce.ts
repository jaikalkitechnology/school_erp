/** Shared helper for coercing Pydantic v2 Decimal-as-string fields back
 *  to numbers. Pydantic serialises Decimal columns as JSON strings (e.g.
 *  "1500.00") to preserve precision; React components that call
 *  `.toFixed()` on the resulting field will throw at runtime. Wrap every
 *  numeric field returned by the API in `n()` (and Record<string,decimal>
 *  in `numMap`) at the api.ts layer so the rest of the app keeps its
 *  number typing honest. */

export const n = (v: unknown): number => {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const parsed = Number(v);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

export const nOrNull = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const parsed = Number(v);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

export const numMap = (
  m: Record<string, unknown> | null | undefined,
): Record<string, number> => {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(m ?? {})) out[k] = n(v);
  return out;
};
