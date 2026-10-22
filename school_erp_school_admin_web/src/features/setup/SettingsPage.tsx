import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, Save, Trash2 } from "lucide-react";
import { SchoolLogo } from "@/components/SchoolLogo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ColorField, HEX } from "@/components/ColorField";
import { uploadSchoolLogo } from "@/lib/branding-api";
import { fetchSettings, updateSettings, type SchoolSettings } from "./api";

type FieldKind = "text" | "phone" | "email" | "pincode" | "color";
const FIELDS: {
  key: keyof SchoolSettings;
  label: string;
  placeholder?: string;
  kind?: FieldKind;
}[] = [
  { key: "school_name", label: "School name" },
  { key: "primary_color", label: "Primary colour", kind: "color" },
  { key: "secondary_color", label: "Secondary colour", kind: "color" },
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
      if (f.kind === "color" && !HEX.test(v))
        errs[f.key] = "Use a colour like #E85D2E";
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
      qc.invalidateQueries({ queryKey: ["branding"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2_000);
    },
  });

  // Logo upload/remove save straight away (only logo_url), so the sidebar
  // updates without touching any other unsaved edits on this form.
  const logoInput = useRef<HTMLInputElement>(null);
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoMsg, setLogoMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const setLogo = async (next: () => Promise<string | null>, okText: string) => {
    setLogoBusy(true);
    setLogoMsg(null);
    try {
      const logo_url = await next();
      const res = await updateSettings({ logo_url });
      setForm((s) => ({ ...s, logo_url: res.logo_url }));
      qc.invalidateQueries({ queryKey: ["branding"] });
      setLogoMsg({ ok: true, text: okText });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setLogoMsg({
        ok: false,
        text: typeof detail === "string" ? detail : "Couldn't update the logo. Use a PNG, JPG or SVG image.",
      });
    } finally {
      setLogoBusy(false);
    }
  };

  const onLogoFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow picking the same file again
    if (file) setLogo(() => uploadSchoolLogo(file), "Logo updated. It now shows at the top of the sidebar.");
  };

  if (settings.isLoading) return <p className="text-sm text-muted-foreground">Loading settings…</p>;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Phase 4 · School foundation</p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Settings</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Branding + identity. The logo and school name update in the sidebar right away;
          other staff see them within a few minutes.
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
            <div className="col-span-2 flex flex-wrap items-center gap-4 rounded-lg border border-saffron-pale p-4">
              <SchoolLogo
                src={form.logo_url}
                alt="School logo"
                className="h-20 w-20 shrink-0 rounded-lg border border-saffron-pale bg-white object-contain p-1.5"
                fallback={
                  <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg border border-dashed border-saffron-pale text-xs text-muted-foreground">
                    No logo
                  </div>
                }
              />
              <div className="min-w-0 flex-1 space-y-2">
                <div>
                  <p className="text-sm font-medium text-indigo-dark">School logo</p>
                  <p className="text-xs text-muted-foreground">
                    PNG, JPG or SVG; a square image works best. Shows at the top of the
                    sidebar and on printed ID cards.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <input
                    ref={logoInput}
                    id="logo-file"
                    type="file"
                    accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
                    className="hidden"
                    onChange={onLogoFile}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={logoBusy}
                    onClick={() => logoInput.current?.click()}
                  >
                    <ImageUp className="h-4 w-4" />
                    {logoBusy ? "Saving…" : form.logo_url ? "Replace logo" : "Upload logo"}
                  </Button>
                  {form.logo_url && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={logoBusy}
                      onClick={() => setLogo(async () => null, "Logo removed.")}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" /> Remove
                    </Button>
                  )}
                </div>
                {logoMsg && (
                  <p className={logoMsg.ok ? "text-xs text-teal-dark" : "text-xs text-destructive"}>
                    {logoMsg.text}
                  </p>
                )}
              </div>
            </div>

            {FIELDS.map((f) =>
              f.kind === "color" ? (
                <ColorField
                  key={f.key}
                  id={f.key}
                  label={f.label}
                  value={(form[f.key] as string | null | undefined) ?? ""}
                  onChange={(v) => {
                    setForm((s) => ({ ...s, [f.key]: v }));
                    if (fieldErrors[f.key])
                      setFieldErrors((p) => {
                        const n = { ...p };
                        delete n[f.key];
                        return n;
                      });
                  }}
                  error={fieldErrors[f.key]}
                />
              ) : (
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
              ),
            )}
            <div className="col-span-2 flex items-center justify-end">
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
