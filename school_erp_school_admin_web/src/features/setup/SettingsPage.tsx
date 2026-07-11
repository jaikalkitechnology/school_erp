import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchSettings, updateSettings, type SchoolSettings } from "./api";

type FieldKind = "text" | "phone" | "email" | "pincode";
const FIELDS: {
  key: keyof SchoolSettings;
  label: string;
  placeholder?: string;
  kind?: FieldKind;
}[] = [
  { key: "school_name", label: "School name" },
  { key: "primary_color", label: "Primary colour", placeholder: "#E85D2E" },
  { key: "secondary_color", label: "Secondary colour", placeholder: "#0F766E" },
  { key: "logo_url", label: "Logo URL" },
  { key: "timezone", label: "Timezone", placeholder: "Asia/Kolkata" },
  { key: "affiliation_board", label: "Affiliation board", placeholder: "CBSE / ICSE / State" },
  { key: "medium", label: "Medium", placeholder: "English" },
  { key: "address", label: "Address" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "pincode", label: "PIN", kind: "pincode" },
  { key: "phone", label: "Phone", kind: "phone" },
  { key: "email", label: "Email", kind: "email" },
];

export function SettingsPage() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: fetchSettings });
  const [form, setForm] = useState<Partial<SchoolSettings>>({});
  const [saved, setSaved] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): Record<string, string> => {
    const errs: Record<string, string> = {};
    for (const f of FIELDS) {
      const v = String((form[f.key] as string | null | undefined) ?? "").trim();
      if (v === "") continue; // all optional
      if (f.kind === "phone" && v.replace(/\D/g, "").length !== 10)
        errs[f.key] = "Enter a 10-digit phone number";
      if (f.kind === "pincode" && !/^\d{6}$/.test(v))
        errs[f.key] = "PIN must be 6 digits";
      if (f.kind === "email" && !/^[a-zA-Z0-9.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(v))
        errs[f.key] = "Enter a valid email address";
    }
    return errs;
  };

  useEffect(() => {
    if (settings.data) setForm(settings.data);
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => updateSettings(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2_000);
    },
  });

  if (settings.isLoading) return <p className="text-sm text-muted-foreground">Loading settings…</p>;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 4 · School foundation</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Settings</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Branding + identity. Changes are visible to every user the next time they sign in.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>School identity</CardTitle>
          <CardDescription>Edit any field, then click Save.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-2 gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              const errs = validate();
              setFieldErrors(errs);
              if (Object.keys(errs).length > 0) return;
              save.mutate();
            }}
          >
            {FIELDS.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label htmlFor={f.key}>{f.label}</Label>
                <Input
                  id={f.key}
                  type={f.kind === "email" ? "email" : f.kind === "phone" ? "tel" : "text"}
                  inputMode={f.kind === "phone" || f.kind === "pincode" ? "numeric" : undefined}
                  maxLength={f.kind === "phone" ? 10 : f.kind === "pincode" ? 6 : undefined}
                  placeholder={f.placeholder}
                  value={(form[f.key] as string | null | undefined) ?? ""}
                  onChange={(e) => {
                    let v = e.target.value;
                    if (f.kind === "phone") v = v.replace(/\D/g, "").slice(0, 10);
                    else if (f.kind === "pincode") v = v.replace(/\D/g, "").slice(0, 6);
                    setForm((s) => ({ ...s, [f.key]: v }));
                    if (fieldErrors[f.key])
                      setFieldErrors((p) => {
                        const n = { ...p };
                        delete n[f.key];
                        return n;
                      });
                  }}
                  className={fieldErrors[f.key] ? "border-destructive" : undefined}
                />
                {fieldErrors[f.key] && (
                  <p className="text-xs text-destructive">{fieldErrors[f.key]}</p>
                )}
              </div>
            ))}
            <div className="col-span-2 flex items-center justify-between">
              <div className="flex gap-3">
                <span className="block h-12 w-24 rounded-md" style={{ background: form.primary_color || "#E85D2E" }} />
                <span className="block h-12 w-24 rounded-md" style={{ background: form.secondary_color || "#0F766E" }} />
              </div>
              <div className="flex items-center gap-3">
                {saved && <span className="text-sm text-teal-dark">Saved.</span>}
                <Button type="submit" disabled={save.isPending}>
                  <Save className="h-4 w-4" />
                  {save.isPending ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
