import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Bell, CheckCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "@/lib/notifications-api";

// Backend timestamps come without a zone; they are UTC.
function parseTs(ts: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts}Z`);
}

function timeAgo(ts: string): string {
  const d = parseTs(ts);
  return Number.isNaN(d.getTime()) ? "" : formatDistanceToNow(d, { addSuffix: true });
}

/** Bell in the top bar: unread badge + a panel of recent notifications. */
export function NotificationBell() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const unread = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => listNotifications({ only_unread: true, limit: 100 }),
    refetchInterval: 60_000,
  });
  const recent = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => listNotifications({ limit: 30 }),
    enabled: open,
  });

  const refresh = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  const markOne = useMutation({ mutationFn: markNotificationRead, onSuccess: refresh });
  const markAll = useMutation({ mutationFn: markAllNotificationsRead, onSuccess: refresh });

  // Close on outside click or Esc.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const count = unread.data?.length ?? 0;
  const badge = count > 99 ? "99+" : String(count);

  const openItem = (n: AppNotification) => {
    if (!n.read_at) markOne.mutate(n.id);
    // Only follow links that point inside this admin app.
    if (n.deeplink && n.deeplink.startsWith("/") && !n.deeplink.startsWith("//")) {
      setOpen(false);
      navigate(n.deeplink);
    }
  };

  return (
    <div className="relative" ref={wrapRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
        className={cn(
          "relative rounded-full p-2 text-indigo-dark transition-colors hover:bg-saffron-pale/70",
          open && "bg-saffron-pale",
        )}
      >
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-saffron px-1 text-[10px] font-bold leading-none text-white ring-2 ring-warm-white">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 top-full z-50 mt-2 w-[min(380px,calc(100vw-2rem))] overflow-hidden rounded-xl border border-saffron-pale bg-warm-white shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-saffron-pale px-4 py-3">
            <div>
              <p className="font-display text-base font-semibold text-indigo-dark">Notifications</p>
              <p className="text-xs text-muted-foreground">
                {count ? `${count} unread` : "You're all caught up"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => markAll.mutate()}
              disabled={count === 0 || markAll.isPending}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-saffron-darker hover:bg-saffron-pale/60 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          </div>

          <div className="max-h-[min(420px,70vh)] overflow-y-auto">
            {recent.isLoading ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">Loading…</p>
            ) : recent.isError ? (
              <p className="px-4 py-8 text-center text-sm text-destructive">
                Couldn't load notifications. Check your connection and try again.
              </p>
            ) : !recent.data?.length ? (
              <div className="px-4 py-10 text-center">
                <Bell className="mx-auto h-6 w-6 text-muted-foreground/60" />
                <p className="mt-2 text-sm text-muted-foreground">No notifications yet.</p>
              </div>
            ) : (
              <ul className="divide-y divide-saffron-pale/70">
                {recent.data.map((n) => {
                  const isUnread = !n.read_at;
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => openItem(n)}
                        className={cn(
                          "flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-saffron-pale/40",
                          isUnread && "bg-saffron-pale/25",
                        )}
                      >
                        <span
                          className={cn(
                            "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                            isUnread ? "bg-saffron" : "bg-transparent",
                          )}
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1">
                          <span className={cn("block text-sm text-indigo-dark", isUnread && "font-semibold")}>
                            {n.title}
                          </span>
                          <span className="mt-0.5 line-clamp-2 block text-xs text-muted-foreground">
                            {n.body}
                          </span>
                          <span className="mt-1 block text-[11px] text-muted-foreground/80">
                            {timeAgo(n.created_at)}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
