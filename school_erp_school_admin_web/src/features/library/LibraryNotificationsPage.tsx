import { useEffect, useState } from "react";
import { Bell, MessageSquare, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LibraryHeader } from "./_shared";

interface Template {
  id: string;
  title: string;
  when: string;
  channel: "SMS" | "Push" | "Email";
  body: string;
}

const DEFAULTS: Template[] = [
  {
    id: "due-soon",
    title: "Due in 2 days",
    when: "48h before the due date",
    channel: "Push",
    body:
      "Hi {{borrower}}, your book \"{{title}}\" is due on {{due}}. Renew or return at the library desk.",
  },
  {
    id: "overdue-day-1",
    title: "Overdue · day 1",
    when: "1 day after the due date",
    channel: "SMS",
    body:
      "Reminder: \"{{title}}\" was due on {{due}}. Fine so far: ₹{{fine}}. Please return it today.",
  },
  {
    id: "overdue-day-7",
    title: "Overdue · day 7",
    when: "7 days after the due date",
    channel: "SMS",
    body:
      "Second reminder: \"{{title}}\" is 7 days overdue. Fine so far: ₹{{fine}}. Contact the librarian.",
  },
  {
    id: "reservation-ready",
    title: "Reservation ready",
    when: "As soon as a reserved copy is returned",
    channel: "Push",
    body:
      "Good news, {{borrower}} — your reservation for \"{{title}}\" is ready. Pick it up within 24 hours.",
  },
];

const STORE_KEY = "jaikalki.library.notification-templates.v1";

/** Library notification templates. Editable client-side; wiring to
 * the comms notification pipeline arrives later. Each template
 * shows when it would fire, which channel it uses, and the body
 * with mustache-style placeholders. */
export function LibraryNotificationsPage() {
  const [templates, setTemplates] = useState<Template[]>(DEFAULTS);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) setTemplates(JSON.parse(raw) as Template[]);
    } catch {
      // ignore
    }
  }, []);

  const save = () => {
    localStorage.setItem(STORE_KEY, JSON.stringify(templates));
    setSavedAt(new Date().toLocaleTimeString());
  };

  const updateOne = (id: string, patch: Partial<Template>) =>
    setTemplates((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    );

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Notifications"
        subtitle="Automated messages sent to borrowers. Edit the wording here — hook to the comms pipeline arrives next."
      />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {savedAt ? `Saved at ${savedAt}.` : "Changes are held locally until you save."}
        </p>
        <Button onClick={save}>
          <Save className="mr-1 h-4 w-4" /> Save templates
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {templates.map((t) => (
          <Card key={t.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                {t.channel === "SMS" ? (
                  <MessageSquare className="h-4 w-4 text-saffron-darker" />
                ) : (
                  <Bell className="h-4 w-4 text-saffron-darker" />
                )}
                {t.title}
              </CardTitle>
              <CardDescription>Fires: {t.when}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Channel
                </label>
                <select
                  className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                  value={t.channel}
                  onChange={(e) =>
                    updateOne(t.id, { channel: e.target.value as Template["channel"] })
                  }
                >
                  <option>SMS</option>
                  <option>Push</option>
                  <option>Email</option>
                </select>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Message
                </label>
                <textarea
                  className="mt-1 w-full rounded border border-input bg-transparent p-2 text-sm"
                  rows={3}
                  value={t.body}
                  onChange={(e) => updateOne(t.id, { body: e.target.value })}
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  Placeholders: <span className="font-mono">{"{{borrower}}"}</span>{" "}
                  <span className="font-mono">{"{{title}}"}</span>{" "}
                  <span className="font-mono">{"{{due}}"}</span>{" "}
                  <span className="font-mono">{"{{fine}}"}</span>
                </p>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Trigger label
                </label>
                <Input
                  value={t.when}
                  onChange={(e) => updateOne(t.id, { when: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
