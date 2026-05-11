import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone, Inbox, FileSliders } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listClasses, listSections } from "@/features/setup/api";
import {
  createAnnouncement,
  listAnnouncements,
  listOutbox,
  listTemplates,
  upsertTemplate,
  type Audience,
  type Channel,
  type DeliveryStatus,
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

const TABS = ["Announcements", "Templates", "Outbox"] as const;
type Tab = (typeof TABS)[number];

export function CommunicationPage() {
  const [tab, setTab] = useState<Tab>("Announcements");
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
            onClick={() => setTab(label)}
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
      {tab === "Templates" && <TemplatesPanel />}
      {tab === "Outbox" && <OutboxPanel />}
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
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      createAnnouncement({
        title,
        body,
        audience,
        audience_id: audience === "class" || audience === "section" ? Number(audienceId) || undefined : undefined,
        is_pinned: pinned,
        publish: true,
      }),
    onSuccess: (res) => {
      setLastResult(`Published. Notified ${res.fanned_out_to} user${res.fanned_out_to === 1 ? "" : "s"}.`);
      setTitle(""); setBody(""); setPinned(false); setAudienceId("");
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
          <CardDescription>Pick an audience; we'll fan it out as in-app notifications instantly.</CardDescription>
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
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="h-4 w-4 accent-saffron" checked={pinned} onChange={(e) => setPinned(e.target.checked)} />
            Pin to the top
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {lastResult && <p className="text-sm text-teal-dark">{lastResult}</p>}
          <Button onClick={() => create.mutate()} disabled={!title || !body || create.isPending}>
            Publish
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent announcements</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!list.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {list.data.map((a) => (
                <li key={a.id} className="px-6 py-3 text-sm">
                  <p className="font-medium text-indigo-dark">
                    {a.is_pinned && <span className="mr-2 text-saffron">★</span>}
                    {a.title}
                  </p>
                  <p className="text-xs text-muted-foreground">{a.body}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-wider text-saffron-dark">
                    {a.audience}
                    {a.audience_id ? ` · #${a.audience_id}` : ""}
                    {a.published_at ? ` · ${new Date(a.published_at).toLocaleString()}` : " · draft"}
                  </p>
                </li>
              ))}
            </ul>
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
