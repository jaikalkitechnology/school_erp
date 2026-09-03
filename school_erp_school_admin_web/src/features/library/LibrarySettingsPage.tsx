import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LibraryHeader } from "./_shared";
import { getLibrarySettings, updateLibrarySettings, type LibrarySettings } from "./api";

/** Library lending policy — now server-backed (one row per school), so the
 * whole team shares the same defaults. New loans read these values. */
export function LibrarySettingsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["library-settings"], queryFn: getLibrarySettings });

  const [form, setForm] = useState<LibrarySettings>({
    loan_days: 14,
    fine_per_day: 1,
    max_books_per_borrower: 3,
    reservation_expiry_days: 3,
  });
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: () => updateLibrarySettings(form),
    onSuccess: (res) => {
      qc.setQueryData(["library-settings"], res);
      setSavedAt(new Date().toLocaleTimeString());
    },
  });

  const num = (k: keyof LibrarySettings, min = 0) => (
    <Input
      type="number"
      min={min}
      value={String(form[k])}
      onChange={(e) => setForm({ ...form, [k]: Math.max(min, Number(e.target.value) || 0) })}
    />
  );

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Library settings"
        subtitle="Lending policy for the whole school. Applied when a book is issued or reserved."
      />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {savedAt ? `Saved at ${savedAt}.` : "Shared across the library team."}
        </p>
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          <Save className="mr-1 h-4 w-4" /> {save.isPending ? "Saving…" : "Save settings"}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Loan policy</CardTitle>
            <CardDescription>How long a book stays out and how many at once.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Loan period (days)</Label>
              {num("loan_days", 1)}
            </div>
            <div>
              <Label>Max books / borrower</Label>
              {num("max_books_per_borrower", 1)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fines & reservations</CardTitle>
            <CardDescription>Charged per day past due; reservation hold window.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <div>
              <Label>Fine · ₹ / day</Label>
              {num("fine_per_day", 0)}
            </div>
            <div>
              <Label>Reservation hold (days)</Label>
              {num("reservation_expiry_days", 1)}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
