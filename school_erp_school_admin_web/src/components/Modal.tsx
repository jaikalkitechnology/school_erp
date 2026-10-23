import { X } from "lucide-react";

/** Message from an API error (the backend explains refusals in `detail`). */
export function apiError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" && detail !== "Validation error" ? detail : fallback;
}

/** Small centred dialog (a bottom sheet on phones). Clicking the backdrop closes it. */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div role="dialog" aria-label={title} className="w-full max-w-md rounded-t-lg bg-warm-white p-5 shadow-lg sm:rounded-lg">
        <div className="mb-4 flex items-start justify-between">
          <h2 className="font-display text-lg text-indigo-dark">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted-foreground hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
