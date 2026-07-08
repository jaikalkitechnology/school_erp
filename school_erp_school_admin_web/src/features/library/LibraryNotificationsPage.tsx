import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, MessageSquare, Save, Send, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  borrowerSearch,
  listLibraryTemplates,
  notificationDiagnostics,
  notificationTestSend,
  updateLibraryTemplate,
  type BorrowerRow,
  type LibraryTemplate,
  type NotifChannel,
  type NotifDiagnostics,
  type TestSendResult,
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

      <DiagnosticsPanel />

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

// ---- Diagnostics panel --------------------------------------------------

function DiagnosticsPanel() {
  const [borrowerKind, setBorrowerKind] = useState<"student" | "teacher">("student");
  const [picked, setPicked] = useState<BorrowerRow | null>(null);
  const [diag, setDiag] = useState<NotifDiagnostics | null>(null);
  const [testResult, setTestResult] = useState<TestSendResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const load = useMutation({
    mutationFn: () =>
      notificationDiagnostics(
        picked ? { kind: borrowerKind, id: picked.id } : undefined,
      ),
    onSuccess: (d) => {
      setDiag(d);
      setTestResult(null);
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Diagnostics failed.");
    },
  });

  const test = useMutation({
    mutationFn: () => notificationTestSend(borrowerKind, picked!.id),
    onSuccess: (r) => {
      setTestResult(r);
      setErrorMsg(null);
      // Refresh diagnostics so the recent outbox rows appear.
      load.mutate();
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Test send failed.");
    },
  });

  return (
    <Card className="border-marigold-pale bg-marigold-pale/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Stethoscope className="h-4 w-4" /> Diagnostics
        </CardTitle>
        <CardDescription>
          Verify the pipeline is wired end-to-end. Search for a real
          student or teacher, click "Run check" to see who would be
          notified + their FCM device count, then "Send test" to fire
          the "library.issued" template at them right now.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-[140px_1fr_auto_auto] gap-3">
          <div>
            <Label>Borrower type</Label>
            <select
              className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={borrowerKind}
              onChange={(e) => {
                setBorrowerKind(e.target.value as "student" | "teacher");
                setPicked(null);
              }}
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>
          <div>
            <Label>Borrower</Label>
            <BorrowerPicker
              kind={borrowerKind}
              picked={picked}
              onPick={setPicked}
            />
          </div>
          <div className="flex items-end">
            <Button variant="outline" onClick={() => load.mutate()} disabled={load.isPending}>
              Run check
            </Button>
          </div>
          <div className="flex items-end">
            <Button
              onClick={() => test.mutate()}
              disabled={!picked || test.isPending}
            >
              <Send className="mr-1 h-4 w-4" /> Send test
            </Button>
          </div>
        </div>

        {errorMsg && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {errorMsg}
          </p>
        )}

        {testResult && (
          <div
            className={cn(
              "rounded-md px-3 py-2 text-sm",
              testResult.ok
                ? "bg-teal-pale text-teal-dark"
                : "bg-destructive/10 text-destructive",
            )}
          >
            <p className="font-medium">
              {testResult.ok ? "Test fired." : `Blocked: ${testResult.reason}`}
            </p>
            {testResult.ok && (
              <ul className="mt-1 space-y-0.5 text-xs">
                <li>
                  Recipients: {testResult.recipient_count} —{" "}
                  {testResult.recipients?.map((r) => r.name).join(", ")}
                </li>
                <li>In-app rows created: {testResult.in_app_created}</li>
                <li>
                  Push outbox queued: {testResult.push_outbox_queued}
                  {testResult.push_result &&
                    ` · sent ${testResult.push_result.sent} · failed ${testResult.push_result.failed}`}
                </li>
              </ul>
            )}
          </div>
        )}

        {diag && (
          <div className="space-y-3 text-sm">
            <div>
              <p className="font-semibold">
                Templates: {diag.templates_seeded} of {diag.templates_expected} seeded
              </p>
              <ul className="mt-1 space-y-0.5 text-xs">
                {Object.entries(diag.templates).map(([code, meta]) => (
                  <li key={code}>
                    <span className="font-mono">{code}</span>{" "}
                    {meta.seeded ? (
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[10px]",
                          meta.active
                            ? "bg-teal-pale text-teal-dark"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        {meta.active ? "active" : "disabled"} · {meta.channels.join("/")}
                      </span>
                    ) : (
                      <span className="rounded bg-destructive/15 px-1.5 py-0.5 text-[10px] text-destructive">
                        NOT SEEDED
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {diag.borrower && (
              <div>
                <p className="font-semibold">
                  Recipients for {diag.borrower.kind} #{diag.borrower.id}:{" "}
                  {diag.borrower.recipient_count}
                </p>
                {diag.borrower.recipient_count === 0 ? (
                  <p className="mt-1 text-xs text-destructive">
                    Nobody would be notified — this borrower has no linked User
                    account. For a student, either the student needs a login OR
                    a parent needs to be linked via parent_child_mappings.
                  </p>
                ) : (
                  <ul className="mt-1 space-y-1 text-xs">
                    {diag.borrower.recipients.map((r) => (
                      <li key={r.user_id} className="rounded border border-saffron-pale bg-white p-2">
                        <span className="font-medium">{r.name}</span>{" "}
                        <span className="text-muted-foreground">
                          (user #{r.user_id}, {r.is_active ? "active" : "inactive"})
                        </span>
                        <div className="mt-0.5 text-[11px] text-muted-foreground">
                          phone {r.phone ?? "—"} · email {r.email ?? "—"} · FCM devices{" "}
                          <span
                            className={cn(
                              r.active_devices > 0 ? "text-teal-dark" : "text-destructive",
                            )}
                          >
                            {r.active_devices}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

                {diag.borrower.recent_outbox_rows.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold">
                      Recent notification_outbox rows (last 15 min)
                    </p>
                    <table className="mt-1 w-full text-[11px]">
                      <thead className="text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                        <tr>
                          <th className="py-1">Ch</th>
                          <th>Status</th>
                          <th>Subject</th>
                          <th>Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {diag.borrower.recent_outbox_rows.map((r) => (
                          <tr key={r.id} className="border-t border-saffron-pale">
                            <td className="py-1 font-mono">{r.channel}</td>
                            <td>
                              <span
                                className={cn(
                                  "rounded px-1.5 py-0.5 text-[10px]",
                                  r.status === "sent"
                                    ? "bg-teal-pale text-teal-dark"
                                    : r.status === "failed"
                                    ? "bg-destructive/15 text-destructive"
                                    : "bg-marigold-pale text-marigold-dark",
                                )}
                              >
                                {r.status}
                              </span>
                            </td>
                            <td className="truncate">{r.subject ?? "—"}</td>
                            <td className="text-destructive">{r.error ?? ""}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---- Borrower picker (search + click) -----------------------------------

function BorrowerPicker({
  kind,
  picked,
  onPick,
}: {
  kind: "student" | "teacher";
  picked: BorrowerRow | null;
  onPick: (row: BorrowerRow | null) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  // Debounced query — we don't hammer the backend for every keystroke.
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 200);
    return () => clearTimeout(t);
  }, [q]);

  const { data: results = [], isLoading } = useQuery({
    queryKey: ["library-borrower-search", kind, debounced],
    queryFn: () => borrowerSearch(kind, debounced, 20),
    enabled: open,
  });

  if (picked) {
    return (
      <div className="mt-1 flex h-9 items-center justify-between rounded border border-saffron bg-saffron-pale px-3 text-sm">
        <span>
          <span className="font-semibold text-saffron-darker">{picked.name}</span>{" "}
          <span className="text-xs text-muted-foreground">
            #{picked.id}
            {picked.hint ? ` · ${picked.hint}` : ""}
          </span>
        </span>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-indigo-dark"
          onClick={() => {
            onPick(null);
            setQ("");
            setOpen(true);
          }}
        >
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="relative mt-1">
      <Input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={`Search ${kind} by name${kind === "student" ? " or admission number" : " or phone"}`}
      />
      {open && (
        <div className="absolute left-0 right-0 top-10 z-20 max-h-64 overflow-y-auto rounded-md border border-input bg-warm-white shadow-lg">
          {isLoading ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">Searching…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              No matching {kind}s.
            </p>
          ) : (
            results.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => {
                  onPick(r);
                  setOpen(false);
                }}
                className="flex w-full items-start gap-2 border-t border-saffron-pale/50 px-3 py-2 text-left text-sm first:border-t-0 hover:bg-saffron-pale/60"
              >
                <div className="flex-1">
                  <p className="font-medium text-indigo-dark">{r.name}</p>
                  <p className="text-xs text-muted-foreground">
                    #{r.id}
                    {r.hint ? ` · ${r.hint}` : ""}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
