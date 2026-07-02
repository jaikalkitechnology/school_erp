import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LibraryHeader } from "./_shared";

interface LibrarySettings {
  student_loan_days: number;
  teacher_loan_days: number;
  student_fine_per_day: number;
  teacher_fine_per_day: number;
  max_renewals: number;
  max_active_loans_student: number;
  max_active_loans_teacher: number;
  reservation_expiry_hours: number;
  opening_time: string;
  closing_time: string;
  closed_days: string;
  notify_sms: boolean;
  notify_push: boolean;
  notify_email: boolean;
}

const DEFAULTS: LibrarySettings = {
  student_loan_days: 14,
  teacher_loan_days: 30,
  student_fine_per_day: 2,
  teacher_fine_per_day: 5,
  max_renewals: 2,
  max_active_loans_student: 3,
  max_active_loans_teacher: 10,
  reservation_expiry_hours: 24,
  opening_time: "08:00",
  closing_time: "17:00",
  closed_days: "Sunday",
  notify_sms: true,
  notify_push: true,
  notify_email: false,
};

const STORE_KEY = "jaikalki.library.settings.v1";

/** Library-wide defaults. Held in localStorage until a
 * server-backed settings model ships — the Books page still reads
 * per-title overrides from the backend, so the impact of these
 * defaults is only on new books + policy displays. */
export function LibrarySettingsPage() {
  const [s, setS] = useState<LibrarySettings>(DEFAULTS);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) setS({ ...DEFAULTS, ...(JSON.parse(raw) as Partial<LibrarySettings>) });
    } catch {
      // ignore
    }
  }, []);

  const save = () => {
    localStorage.setItem(STORE_KEY, JSON.stringify(s));
    setSavedAt(new Date().toLocaleTimeString());
  };

  const num = (k: keyof LibrarySettings) => (
    <Input
      value={String(s[k])}
      onChange={(e) => setS({ ...s, [k]: Number(e.target.value) || 0 })}
    />
  );
  const txt = (k: keyof LibrarySettings) => (
    <Input
      value={String(s[k])}
      onChange={(e) => setS({ ...s, [k]: e.target.value })}
    />
  );
  const bool = (k: keyof LibrarySettings) => (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={Boolean(s[k])}
        onChange={(e) => setS({ ...s, [k]: e.target.checked })}
      />
      Enabled
    </label>
  );

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Library settings"
        subtitle="Module-wide defaults. Applied to newly created books and referenced by the notification templates."
      />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {savedAt ? `Saved at ${savedAt}.` : "Changes are held locally until you save."}
        </p>
        <Button onClick={save}>
          <Save className="mr-1 h-4 w-4" /> Save settings
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Loan policy</CardTitle>
            <CardDescription>How long a book can stay out, per borrower type.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Student loan (days)</Label>
              {num("student_loan_days")}
            </div>
            <div>
              <Label>Teacher loan (days)</Label>
              {num("teacher_loan_days")}
            </div>
            <div>
              <Label>Max active loans / student</Label>
              {num("max_active_loans_student")}
            </div>
            <div>
              <Label>Max active loans / teacher</Label>
              {num("max_active_loans_teacher")}
            </div>
            <div>
              <Label>Max renewals per loan</Label>
              {num("max_renewals")}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fines</CardTitle>
            <CardDescription>Charged per day once past the due date.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Student · ₹ / day</Label>
              {num("student_fine_per_day")}
            </div>
            <div>
              <Label>Teacher · ₹ / day</Label>
              {num("teacher_fine_per_day")}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Reservations</CardTitle>
            <CardDescription>How long a "ready" reservation waits for pickup.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Ready-window (hours)</Label>
              {num("reservation_expiry_hours")}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Opening hours</CardTitle>
            <CardDescription>Fine calculation skips closed days.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Opens at</Label>
              {txt("opening_time")}
            </div>
            <div>
              <Label>Closes at</Label>
              {txt("closing_time")}
            </div>
            <div className="col-span-2">
              <Label>Closed days</Label>
              {txt("closed_days")}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>Which channels the Notifications page can use.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-3">
            <div>
              <Label>SMS</Label>
              {bool("notify_sms")}
            </div>
            <div>
              <Label>Push</Label>
              {bool("notify_push")}
            </div>
            <div>
              <Label>Email</Label>
              {bool("notify_email")}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
