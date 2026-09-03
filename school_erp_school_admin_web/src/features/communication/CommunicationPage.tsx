import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone, Inbox, FileSliders, MessageSquareText, Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import {
  bulkDeleteAnnouncements,
  createAnnouncement,
  deleteAnnouncement,
  listAnnouncements,
  listInboxMessages,
  listOutbox,
  listSentMessages,
  listTemplates,
  markMessageRead,
  sendDirectMessage,
  upsertTemplate,
  type Audience,
  type Channel,
  type DeliveryStatus,
  type DirectMessage,
} from "./api";

const AUDIENCES: { value: Audience; label: string }[] = [
  { value: "all", label: "Everyone" },
  { value: "staff", label: "Staff" },
  { value: "parents", label: "Parents" },
  { value: "students", label: "Students" },
  { value: "class", label: "Specific class" },
  { value: "section", label: "Specific section" },
];

const STATUS_TONE: Record<DeliveryStatus, string> = {
  queued: "bg-marigold-pale text-marigold-dark",
  sent: "bg-teal-pale text-teal-dark",
  failed: "bg-destructive/15 text-destructive",
  skipped: "bg-muted text-muted-foreground",
};

const TABS = ["Announcements", "Messages", "Templates", "Outbox"] as const;
type Tab = (typeof TABS)[number];

export function CommunicationPage() {
  const [params, setParams] = useSearchParams();
  const paramTab = params.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(
    paramTab && TABS.includes(paramTab) ? paramTab : "Announcements",
  );
  useEffect(() => {
    const t = params.get("tab") as Tab | null;
    if (t && TABS.includes(t) && t !== tab) setTab(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);
  const selectTab = (t: Tab) => {
    setTab(t);
    setParams({ tab: t }, { replace: true });
  };
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 12 · Communication</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Notice board &amp; messages</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Publish announcements, manage notification templates, and inspect external delivery (SMS,
          email, WhatsApp) queued in the outbox.
        </p>
      </header>
      <nav className="flex gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => selectTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label ? "border-b-2 border-saffron text-saffron-darker" : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "Announcements" && <AnnouncementsPanel />}
      {tab === "Messages" && <MessagesPanel />}
      {tab === "Templates" && <TemplatesPanel />}
      {tab === "Outbox" && <OutboxPanel />}
    </div>
  );
}

// ---- Messages: 1-on-1 inbox / sent / reply ------------------------------

interface MessageThread {
  peerUserId: number;
  peerName: string;
  lastBody: string;
  lastAt: string;
  unread: number;
}

function buildThreads(
  inbox: DirectMessage[],
  sent: DirectMessage[],
): MessageThread[] {
  const map = new Map<number, MessageThread>();
  const upsert = (peer: number, name: string) => {
    if (!map.has(peer)) {
      map.set(peer, { peerUserId: peer, peerName: name, lastBody: "", lastAt: "", unread: 0 });
    }
    return map.get(peer)!;
  };
  for (const m of inbox) {
    const peer = m.sender_user_id ?? 0;
    if (!peer) continue;
    const t = upsert(peer, m.sender_name || m.sender_full_name || `User #${peer}`);
    if ((m.created_at ?? "") > t.lastAt) {
      t.lastAt = m.created_at;
      t.lastBody = m.body;
    }
    if (!m.read_at) t.unread += 1;
  }
  for (const m of sent) {
    const peer = m.recipient_user_id;
    const t = upsert(peer, `User #${peer}`);
    if ((m.created_at ?? "") > t.lastAt) {
      t.lastAt = m.created_at;
      t.lastBody = `You: ${m.body}`;
    }
  }
  return Array.from(map.values()).sort((a, b) => (b.lastAt || "").localeCompare(a.lastAt || ""));
}

function MessagesPanel() {
  const qc = useQueryClient();
  const inboxQ = useQuery({ queryKey: ["messages-inbox"], queryFn: listInboxMessages });
  const sentQ = useQuery({ queryKey: ["messages-sent"], queryFn: listSentMessages });

  const meUserIdRef = useRef<number>(0);
  useEffect(() => {
    // We don't import the auth store here — derive meUserId from sent
    // messages instead: any row's sender_user_id is us.
    if (sentQ.data && sentQ.data.length > 0 && sentQ.data[0].sender_user_id) {
      meUserIdRef.current = sentQ.data[0].sender_user_id;
    }
  }, [sentQ.data]);

  const threads = useMemo(
    () => buildThreads(inboxQ.data ?? [], sentQ.data ?? []),
    [inboxQ.data, sentQ.data],
  );
  const [activePeer, setActivePeer] = useState<MessageThread | null>(null);

  useEffect(() => {
    if (!activePeer && threads.length > 0) setActivePeer(threads[0]);
  }, [activePeer, threads]);

  const threadMessages = useMemo(() => {
    if (!activePeer) return [] as DirectMessage[];
    const peer = activePeer.peerUserId;
    const all: DirectMessage[] = [
      ...(inboxQ.data ?? []).filter((m) => m.sender_user_id === peer),
      ...(sentQ.data ?? []).filter((m) => m.recipient_user_id === peer),
    ];
    all.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
    return all;
  }, [activePeer, inboxQ.data, sentQ.data]);

  const markRead = useMutation({
    mutationFn: markMessageRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messages-inbox"] }),
  });

  useEffect(() => {
    if (!activePeer) return;
    for (const m of inboxQ.data ?? []) {
      if (m.sender_user_id === activePeer.peerUserId && !m.read_at) {
        markRead.mutate(m.id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePeer?.peerUserId, inboxQ.data]);

  const [reply, setReply] = useState("");
  const send = useMutation({
    mutationFn: (body: string) =>
      sendDirectMessage({ recipient_user_id: activePeer!.peerUserId, body }),
    onSuccess: () => {
      setReply("");
      qc.invalidateQueries({ queryKey: ["messages-sent"] });
      qc.invalidateQueries({ queryKey: ["messages-inbox"] });
    },
  });

  if (inboxQ.isLoading || sentQ.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (threads.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText className="h-5 w-5" /> Inbox
          </CardTitle>
          <CardDescription>
            1-on-1 messages from teachers and parents will appear here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No messages yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-[280px_1fr]">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquareText className="h-4 w-4" /> Conversations
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 p-2">
          {threads.map((th) => {
            const active = activePeer?.peerUserId === th.peerUserId;
            return (
              <button
                key={th.peerUserId}
                onClick={() => setActivePeer(th)}
                className={cn(
                  "w-full rounded-md px-3 py-2 text-left text-sm",
                  active ? "bg-saffron-pale text-indigo-dark" : "hover:bg-muted",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={cn("truncate font-semibold", th.unread > 0 && "text-saffron-darker")}>
                    {th.peerName}
                  </span>
                  {th.unread > 0 && (
                    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-saffron px-1.5 text-[10px] font-bold text-white">
                      {th.unread}
                    </span>
                  )}
                </div>
                <p className="line-clamp-1 text-xs text-muted-foreground">{th.lastBody}</p>
              </button>
            );
          })}
        </CardContent>
      </Card>

      <Card className="flex min-h-[420px] flex-col">
        <CardHeader className="border-b border-saffron-pale pb-3">
          <CardTitle className="text-base">{activePeer?.peerName ?? "Select a conversation"}</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 space-y-3 overflow-y-auto py-4">
          {threadMessages.map((m) => {
            const mine = m.sender_user_id === meUserIdRef.current;
            return (
              <div key={m.id} className={cn("flex", mine ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[72%] rounded-2xl px-3 py-2 text-sm",
                    mine
                      ? "rounded-br-sm bg-saffron text-white"
                      : "rounded-bl-sm border border-saffron-pale bg-background text-indigo-dark",
                  )}
                >
                  {m.subject && (
                    <p className={cn("text-[10px] font-bold uppercase tracking-wide", mine ? "text-white/85" : "text-muted-foreground")}>
                      {m.subject}
                    </p>
                  )}
                  <p className="whitespace-pre-wrap">{m.body}</p>
                  <p className={cn("mt-1 text-[10px]", mine ? "text-white/80" : "text-muted-foreground")}>
                    {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                  </p>
                </div>
              </div>
            );
          })}
        </CardContent>
        {activePeer && (
          <div className="flex items-end gap-2 border-t border-saffron-pale p-3">
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              rows={2}
              placeholder="Type a reply…"
              className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <Button
              onClick={() => reply.trim() && send.mutate(reply.trim())}
              disabled={!reply.trim() || send.isPending}
              className="bg-saffron text-white hover:bg-saffron-dark"
            >
              <Send className="mr-1 h-4 w-4" /> Send
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}

// ---- Announcements --------------------------------------------------------

function AnnouncementsPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["announcements"], queryFn: listAnnouncements });
  const classes = useQuery({ queryKey: ["classes"], queryFn: listClasses });
  const sections = useQuery({ queryKey: ["sections"], queryFn: () => listSections() });

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<Audience>("all");
  const [audienceId, setAudienceId] = useState<number | "">("");
  const [pinned, setPinned] = useState(false);
  // Default on: most announcements should buzz the phone.
  const [sendPush, setSendPush] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  // Per-row ticks for bulk delete. Cleared after each successful mutation.
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const removeOne = useMutation({
    mutationFn: (id: number) => deleteAnnouncement(id),
    onSuccess: (res) => {
      setDeleteError(null);
      setSelected((s) => {
        const next = new Set(s);
        next.delete(res.deleted);
        return next;
      });
      setLastResult(
        `Deleted #${res.deleted} — cleared ${res.notifications_removed} inbox entries.`,
      );
      qc.invalidateQueries({ queryKey: ["announcements"] });
    },
    onError: (e: any) =>
      setDeleteError(e?.response?.data?.detail ?? "Could not delete"),
  });

  const removeBulk = useMutation({
    mutationFn: (ids: number[]) => bulkDeleteAnnouncements(ids),
    onSuccess: (res) => {
      setDeleteError(null);
      setSelected(new Set());
      setLastResult(
        `Deleted ${res.deleted.length} announcements — cleared ${res.notifications_removed} inbox entries${
          res.skipped.length ? ` (skipped ${res.skipped.length})` : ""
        }.`,
      );
      qc.invalidateQueries({ queryKey: ["announcements"] });
    },
    onError: (e: any) =>
      setDeleteError(e?.response?.data?.detail ?? "Could not bulk delete"),
  });

  const onTickRow = (id: number, checked: boolean) =>
    setSelected((s) => {
      const next = new Set(s);
      if (checked) next.add(id); else next.delete(id);
      return next;
    });

  const onTickAll = (checked: boolean) => {
    if (!checked) return setSelected(new Set());
    setSelected(new Set((list.data ?? []).map((a) => a.id)));
  };

  const onBulkDelete = () => {
    if (selected.size === 0) return;
    setDeleteError(null);
    const n = selected.size;
    const ok = window.confirm(
      `Delete ${n} selected announcement${n === 1 ? "" : "s"}?\n\n` +
        "Removes the notice from the bulletin AND wipes the in-app inbox entries " +
        "for every recipient. Outbox / SMS / email audit log is preserved.",
    );
    if (ok) removeBulk.mutate(Array.from(selected));
  };

  const onDeleteOne = (id: number, title: string) => {
    setDeleteError(null);
    const ok = window.confirm(
      `Delete "${title}"?\n\n` +
        "Removes the notice and every inbox entry for it.",
    );
    if (ok) removeOne.mutate(id);
  };

  const create = useMutation({
    mutationFn: () =>
      createAnnouncement({
        title,
        body,
        audience,
        audience_id: audience === "class" || audience === "section" ? Number(audienceId) || undefined : undefined,
        is_pinned: pinned,
        publish: true,
        send_push: sendPush,
      }),
    onSuccess: (res) => {
      const inAppLine = `Notified ${res.fanned_out_to} user${res.fanned_out_to === 1 ? "" : "s"} in-app`;
      let pushLine: string;
      if (!sendPush) {
        pushLine = " · push intentionally off";
      } else if (res.push_sent > 0) {
        pushLine = `, pushed to ${res.push_sent} phone${res.push_sent === 1 ? "" : "s"}`;
        if (res.push_failed > 0) {
          pushLine += ` (${res.push_failed} failed)`;
        }
      } else if (res.push_failed > 0) {
        pushLine = ` · ${res.push_failed} push send${res.push_failed === 1 ? "" : "s"} failed`;
      } else {
        pushLine = " · push skipped (no active devices for the audience)";
      }
      setLastResult(`Published. ${inAppLine}${pushLine}.`);
      setTitle(""); setBody(""); setPinned(false); setAudienceId("");
      // Don't reset sendPush — admin's preference stays sticky.
      qc.invalidateQueries({ queryKey: ["announcements"] });
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not publish"),
  });

  const audienceOptions = useMemo(() => {
    if (audience === "class") return (classes.data ?? []).map((c) => ({ value: c.id, label: c.name }));
    if (audience === "section") return (sections.data ?? []).map((s) => ({ value: s.id, label: `Section #${s.id} (class ${s.class_def_id})` }));
    return [];
  }, [audience, classes.data, sections.data]);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Megaphone className="h-5 w-5" /> New announcement</CardTitle>
          <CardDescription>Pick an audience; we'll fan it out as in-app notifications and (by default) a push to every recipient's phone.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Field label="Title" value={title} onChange={setTitle} />
          <div className="space-y-1.5">
            <Label>Body</Label>
            <textarea
              className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <Select label="Audience" value={audience} onChange={(v) => setAudience(v as Audience)} options={AUDIENCES} />
            {(audience === "class" || audience === "section") && (
              <Select
                label={audience === "class" ? "Class" : "Section"}
                value={audienceId}
                onChange={(v) => setAudienceId(v ? Number(v) : "")}
                options={audienceOptions}
              />
            )}
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4 accent-saffron" checked={pinned} onChange={(e) => setPinned(e.target.checked)} />
              Pin to the top
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-saffron"
                checked={sendPush}
                onChange={(e) => setSendPush(e.target.checked)}
              />
              <span>
                Also send push notification
                <span className="ml-2 text-xs text-muted-foreground">
                  Buzzes every recipient's phone via FCM. Uncheck to keep
                  the announcement in-app only.
                </span>
              </span>
            </label>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {lastResult && <p className="text-sm text-teal-dark">{lastResult}</p>}
          <Button onClick={() => create.mutate()} disabled={!title || !body || create.isPending}>
            Publish
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Recent announcements</CardTitle>
            {selected.size > 0 && (
              <CardDescription>{selected.size} selected</CardDescription>
            )}
          </div>
          {selected.size > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={onBulkDelete}
              disabled={removeBulk.isPending}
            >
              <Trash2 className="mr-1 h-4 w-4 text-destructive" />
              Delete selected
            </Button>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <>
              <label className="flex items-center gap-2 border-b border-saffron-pale px-6 py-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-saffron"
                  checked={
                    list.data.length > 0 &&
                    selected.size === list.data.length
                  }
                  ref={(el) => {
                    if (el) {
                      el.indeterminate =
                        selected.size > 0 && selected.size < list.data.length;
                    }
                  }}
                  onChange={(e) => onTickAll(e.target.checked)}
                />
                Select all
              </label>
              <ul className="divide-y divide-saffron-pale">
                {list.data.map((a) => (
                  <li key={a.id} className="flex items-start gap-3 px-6 py-3 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-saffron"
                      checked={selected.has(a.id)}
                      onChange={(e) => onTickRow(a.id, e.target.checked)}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-indigo-dark">
                        {a.is_pinned && <span className="mr-2 text-saffron">★</span>}
                        {a.title}
                      </p>
                      <p className="text-xs text-muted-foreground">{a.body}</p>
                      <p className="mt-1 text-[11px] uppercase tracking-wider text-saffron-dark">
                        {a.audience}
                        {a.audience_id ? ` · #${a.audience_id}` : ""}
                        {a.published_at
                          ? ` · ${new Date(a.published_at).toLocaleString()}`
                          : " · draft"}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Delete"
                      disabled={removeOne.isPending}
                      onClick={() => onDeleteOne(a.id, a.title)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </li>
                ))}
              </ul>
              {deleteError && (
                <p className="border-t bg-destructive/10 px-6 py-2 text-xs text-destructive">
                  {deleteError}
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Templates ------------------------------------------------------------

const ALL_CHANNELS: Channel[] = ["in_app", "sms", "email", "push", "whatsapp"];

function TemplatesPanel() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["comms-templates"], queryFn: listTemplates });
  const [activeCode, setActiveCode] = useState<string | null>(null);

  const active = list.data?.find((t) => t.code === activeCode) ?? list.data?.[0] ?? null;

  return (
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileSliders className="h-5 w-5" /> Templates</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ul className="divide-y divide-saffron-pale">
            {(list.data ?? []).map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  className={cn(
                    "w-full px-6 py-3 text-left text-sm",
                    (active?.id === t.id) && "bg-saffron-pale/40",
                  )}
                  onClick={() => setActiveCode(t.code)}
                >
                  <p className="font-mono text-xs text-saffron-dark">{t.code}</p>
                  <p className="text-xs text-muted-foreground">{t.channels.join(" · ")}</p>
                </button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {active ? (
        <TemplateEditor
          template={active}
          onSaved={() => qc.invalidateQueries({ queryKey: ["comms-templates"] })}
        />
      ) : (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">Pick a template on the left.</CardContent>
        </Card>
      )}
    </div>
  );
}

function TemplateEditor({ template, onSaved }: { template: any; onSaved: () => void }) {
  const [subjectEn, setSubjectEn] = useState(template.subject_en);
  const [bodyEn, setBodyEn] = useState(template.body_en);
  const [subjectHi, setSubjectHi] = useState(template.subject_hi ?? "");
  const [bodyHi, setBodyHi] = useState(template.body_hi ?? "");
  const [subjectMr, setSubjectMr] = useState(template.subject_mr ?? "");
  const [bodyMr, setBodyMr] = useState(template.body_mr ?? "");
  const [channels, setChannels] = useState<Channel[]>(template.channels);

  const toggleChannel = (c: Channel) =>
    setChannels((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));

  const save = useMutation({
    mutationFn: () =>
      upsertTemplate(template.code, {
        code: template.code,
        subject_en: subjectEn,
        body_en: bodyEn,
        subject_hi: subjectHi || null,
        body_hi: bodyHi || null,
        subject_mr: subjectMr || null,
        body_mr: bodyMr || null,
        channels,
      } as any),
    onSuccess: onSaved,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono">{template.code}</CardTitle>
        <CardDescription>
          Use <code>{"{{key}}"}</code> placeholders for substitution. Available keys depend on the trigger.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 lg:grid-cols-2">
          <Field label="English subject" value={subjectEn} onChange={setSubjectEn} />
          <TextArea label="English body" value={bodyEn} onChange={setBodyEn} />
          <Field label="Hindi subject" value={subjectHi} onChange={setSubjectHi} />
          <TextArea label="Hindi body" value={bodyHi} onChange={setBodyHi} />
          <Field label="Marathi subject" value={subjectMr} onChange={setSubjectMr} />
          <TextArea label="Marathi body" value={bodyMr} onChange={setBodyMr} />
        </div>
        <div>
          <Label>Channels</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            {ALL_CHANNELS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => toggleChannel(c)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs font-medium",
                  channels.includes(c)
                    ? "border-saffron bg-saffron-pale text-saffron-darker"
                    : "border-border text-muted-foreground hover:border-saffron-light",
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save template"}
        </Button>
      </CardContent>
    </Card>
  );
}

// ---- Outbox ---------------------------------------------------------------

function OutboxPanel() {
  const [filter, setFilter] = useState<DeliveryStatus | "">("");
  const list = useQuery({ queryKey: ["comms-outbox", filter], queryFn: () => listOutbox(filter || undefined) });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Inbox className="h-5 w-5" /> Outbox</CardTitle>
          <CardDescription>External deliveries (SMS / Email / Push / WhatsApp) waiting for the dispatcher.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <select
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={filter}
              onChange={(e) => setFilter((e.target.value || "") as DeliveryStatus | "")}
            >
              <option value="">Any</option>
              <option value="queued">Queued</option>
              <option value="sent">Sent</option>
              <option value="failed">Failed</option>
              <option value="skipped">Skipped</option>
            </select>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No rows match.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-6 py-3">Channel</th>
                  <th className="px-4 py-3">Address</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">When</th>
                </tr>
              </thead>
              <tbody>
                {list.data.map((row) => (
                  <tr key={row.id} className="border-b last:border-b-0">
                    <td className="px-6 py-2 font-mono text-xs">{row.channel}</td>
                    <td className="px-4 py-2 font-mono text-xs">{row.address ?? "—"}</td>
                    <td className="px-4 py-2">{row.subject ?? row.body.slice(0, 60)}</td>
                    <td className="px-4 py-2">
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] uppercase", STATUS_TONE[row.status])}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- shared bits ---------------------------------------------------------

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <textarea
        className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function Select<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T | "";
  onChange: (v: string) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— pick —</option>
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
