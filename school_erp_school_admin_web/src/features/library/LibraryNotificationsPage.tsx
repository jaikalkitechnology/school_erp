import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, MessageSquare, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  listLibraryTemplates,
  updateLibraryTemplate,
  type LibraryTemplate,
  type NotifChannel,
} from "./api";
import { LibraryHeader } from "./_shared";

// Human labels for each template code — matches the backend spec so
// the librarian sees the *when* not just the machine code.
const META: Record<
  string,
  { title: string; when: string }
> = {
  "library.issued": {
    title: "Book borrowed",
    when: "Immediately after a book is issued at the desk",
  },
  "library.due_soon": {
    title: "Due in 2 days",
    when: "Daily sweep — 48h before due_on",
  },
  "library.overdue_day1": {
    title: "Overdue — day 1",
    when: "As soon as a loan flips past its due date",
  },
  "library.overdue_day7": {
    title: "Overdue — day 7",
    when: "Daily sweep — 7 days past due_on",
  },
  "library.reservation_ready": {
    title: "Reservation ready",
    when: "When a returned copy promotes a pending reservation",
  },
};

const ALL_CHANNELS: NotifChannel[] = ["in_app", "push", "sms", "email"];

/** Library notification templates — read + edit against the real
 * ``notification_templates`` table. Edits here take effect on the
 * next event fire, no server restart needed. */
export function LibraryNotificationsPage() {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: ["library-notif-templates"],
    queryFn: listLibraryTemplates,
  });
  const [draft, setDraft] = useState<Record<string, LibraryTemplate>>({});
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Reset the draft whenever the server data comes back.
  useEffect(() => {
    const map: Record<string, LibraryTemplate> = {};
    for (const t of data) map[t.code] = t;
    setDraft(map);
  }, [data]);

  const save = useMutation({
    mutationFn: async (code: string) => {
      const t = draft[code];
      if (!t) return;
      return updateLibraryTemplate(code, {
        subject_en: t.subject_en,
        body_en: t.body_en,
        channels: t.channels,
        is_active: t.is_active,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-notif-templates"] });
      setSavedAt(new Date().toLocaleTimeString());
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Save failed.");
    },
  });

  const update = (code: string, patch: Partial<LibraryTemplate>) =>
    setDraft((prev) => ({ ...prev, [code]: { ...prev[code], ...patch } }));

  const toggleChannel = (code: string, ch: NotifChannel) => {
    const cur = draft[code]?.channels ?? [];
    const next = cur.includes(ch) ? cur.filter((c) => c !== ch) : [...cur, ch];
    update(code, { channels: next });
  };

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Notifications"
        subtitle="Automated messages to borrowers. Edits here take effect on the next event fire — no restart needed."
      />

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading templates…</p>
      )}

      {savedAt && !errorMsg && (
        <p className="rounded-md bg-teal-pale px-3 py-2 text-sm text-teal-dark">
          Saved at {savedAt}. Next event fire will use the new copy.
        </p>
      )}
      {errorMsg && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errorMsg}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data.map((t) => {
          const meta = META[t.code] ?? { title: t.code, when: "Trigger unknown" };
          const d = draft[t.code] ?? t;
          const isPush = d.channels.includes("push");
          return (
            <Card key={t.code}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {isPush ? (
                    <Bell className="h-4 w-4 text-saffron-darker" />
                  ) : (
                    <MessageSquare className="h-4 w-4 text-saffron-darker" />
                  )}
                  {meta.title}
                  {!d.is_active && (
                    <span className="ml-2 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      disabled
                    </span>
                  )}
                </CardTitle>
                <CardDescription>
                  <span className="font-mono text-[10px] uppercase tracking-wider">
                    {t.code}
                  </span>{" "}
                  · {meta.when}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label>Subject</Label>
                  <Input
                    value={d.subject_en}
                    onChange={(e) => update(t.code, { subject_en: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Body</Label>
                  <textarea
                    className="mt-1 w-full rounded border border-input bg-transparent p-2 text-sm"
                    rows={3}
                    value={d.body_en}
                    onChange={(e) => update(t.code, { body_en: e.target.value })}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    Placeholders: <span className="font-mono">{"{{borrower}}"}</span>{" "}
                    <span className="font-mono">{"{{title}}"}</span>{" "}
                    <span className="font-mono">{"{{due}}"}</span>{" "}
                    <span className="font-mono">{"{{fine}}"}</span>{" "}
                    <span className="font-mono">{"{{fine_per_day}}"}</span>
                  </p>
                </div>
                <div>
                  <Label>Channels</Label>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {ALL_CHANNELS.map((ch) => {
                      const on = d.channels.includes(ch);
                      return (
                        <button
                          key={ch}
                          type="button"
                          onClick={() => toggleChannel(t.code, ch)}
                          className={cn(
                            "rounded-md border px-3 py-1 text-xs uppercase tracking-wide transition-colors",
                            on
                              ? "border-saffron bg-saffron-pale text-saffron-darker"
                              : "border-input text-muted-foreground hover:bg-muted",
                          )}
                        >
                          {ch === "in_app" ? "in app" : ch}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={d.is_active}
                      onChange={(e) => update(t.code, { is_active: e.target.checked })}
                    />
                    Enabled
                  </label>
                  <Button
                    size="sm"
                    onClick={() => save.mutate(t.code)}
                    disabled={save.isPending}
                  >
                    <Save className="mr-1 h-4 w-4" /> Save
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
