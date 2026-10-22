/**
 * Date + time for display, always 12-hour: "22 Oct 2026, 2:30 PM".
 *
 * `toLocaleString()` follows the browser's locale, which for en-IN /
 * en-GB is 24-hour, so format explicitly instead.
 *
 * Two kinds of timestamp reach the UI:
 *  - "utc" (default): set by the server (created_at, an announcement's
 *    published_at). The API sends them without a zone but they are UTC,
 *    so they're converted to the viewer's local time.
 *  - "wall": typed by a person into a date-time box (eg. a notice's
 *    publish / expiry time). Stored exactly as entered, so shown as-is.
 */
export function formatDateTime(ts: string | null | undefined, kind: "utc" | "wall" = "utc"): string {
  if (!ts) return "";
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(ts);
  const iso = ts.replace(" ", "T");
  const d = new Date(kind === "utc" && !hasZone ? `${iso}Z` : iso);
  if (Number.isNaN(d.getTime())) return ts;
  const date = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
  return `${date}, ${time}`;
}
