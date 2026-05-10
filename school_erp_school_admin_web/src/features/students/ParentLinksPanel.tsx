import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createParent,
  linkStudentParent,
  listStudentParents,
  unlinkStudentParent,
  type AccessLevel,
  type Relation,
} from "./parents-api";

const RELATIONS: { value: Relation; label: string }[] = [
  { value: "father", label: "Father" },
  { value: "mother", label: "Mother" },
  { value: "guardian", label: "Guardian" },
  { value: "other", label: "Other" },
];

const LEVELS: { value: AccessLevel; label: string }[] = [
  { value: "primary", label: "Primary (full)" },
  { value: "secondary", label: "Secondary (read-only)" },
  { value: "guardian", label: "Guardian (limited)" },
];

export function ParentLinksPanel({ studentId }: { studentId: number }) {
  const qc = useQueryClient();
  const links = useQuery({
    queryKey: ["student-parents", studentId],
    queryFn: () => listStudentParents(studentId),
  });

  const remove = useMutation({
    mutationFn: (mappingId: number) => unlinkStudentParent(studentId, mappingId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["student-parents", studentId] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Linked parents / guardians</CardTitle>
          <CardDescription>
            Parents are auto-linked when admission carries a phone or email; add more here for second
            guardians, step-parents, etc.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {links.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : !links.data?.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No parents linked yet.</p>
          ) : (
            <ul className="divide-y divide-saffron-pale">
              {links.data.map((link) => (
                <li key={link.mapping_id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium text-indigo-dark">{link.parent_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {link.relation} · {link.access_level}
                      {link.is_primary && (
                        <span className="ml-2 rounded-full bg-teal-pale px-2 py-0.5 text-[10px] uppercase tracking-wider text-teal-dark">
                          primary
                        </span>
                      )}
                    </p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {[link.parent_phone, link.parent_email].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => remove.mutate(link.mapping_id)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AddParentLink studentId={studentId} />
    </div>
  );
}

function AddParentLink({ studentId }: { studentId: number }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"existing" | "create">("create");
  const [parentUserId, setParentUserId] = useState<number | "">("");
  const [relation, setRelation] = useState<Relation>("guardian");
  const [accessLevel, setAccessLevel] = useState<AccessLevel>("primary");
  const [isPrimary, setIsPrimary] = useState(false);
  const [canPayFee, setCanPayFee] = useState(true);
  const [canReceiveNotifications, setCanReceiveNotifications] = useState(true);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      createParent({
        full_name: fullName,
        email: email || undefined,
        phone: phone || undefined,
        password,
        relation,
      }),
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not create parent"),
  });

  const link = useMutation({
    mutationFn: (parent_user_id: number) =>
      linkStudentParent(studentId, {
        parent_user_id,
        relation,
        access_level: accessLevel,
        is_primary: isPrimary,
        can_pay_fee: canPayFee,
        can_receive_notifications: canReceiveNotifications,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["student-parents", studentId] });
      setFullName(""); setEmail(""); setPhone(""); setPassword(""); setParentUserId("");
      setError(null);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "Could not link parent"),
  });

  const submit = async () => {
    setError(null);
    if (mode === "create") {
      const parent = await create.mutateAsync();
      await link.mutateAsync(parent.user_id);
    } else if (parentUserId !== "") {
      await link.mutateAsync(Number(parentUserId));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add parent link</CardTitle>
        <CardDescription>
          Create a new parent account or attach an existing user (by user-id from the Phase 8 listing).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button variant={mode === "create" ? "default" : "outline"} size="sm" onClick={() => setMode("create")}>
            Create new
          </Button>
          <Button variant={mode === "existing" ? "default" : "outline"} size="sm" onClick={() => setMode("existing")}>
            Use existing user-id
          </Button>
        </div>

        {mode === "create" ? (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Full name *" value={fullName} onChange={setFullName} />
            <Field label="Phone" value={phone} onChange={setPhone} />
            <Field label="Email" value={email} onChange={setEmail} />
            <Field label="Password *" value={password} onChange={setPassword} hint="Parent uses this on first login." />
          </div>
        ) : (
          <Field
            label="Parent user_id"
            value={String(parentUserId)}
            onChange={(v) => setParentUserId(v ? Number(v) : "")}
            hint="From the Phase 8 parent listing or Phase 2 user audit."
          />
        )}

        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label="Relation"
            value={relation}
            onChange={(v) => setRelation(v as Relation)}
            options={RELATIONS}
          />
          <SelectField
            label="Access level"
            value={accessLevel}
            onChange={(v) => setAccessLevel(v as AccessLevel)}
            options={LEVELS}
          />
        </div>
        <div className="flex flex-wrap gap-6 text-sm">
          <CheckboxRow label="Primary contact" checked={isPrimary} onChange={setIsPrimary} />
          <CheckboxRow label="Can pay fees" checked={canPayFee} onChange={setCanPayFee} />
          <CheckboxRow
            label="Receives notifications"
            checked={canReceiveNotifications}
            onChange={setCanReceiveNotifications}
          />
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end">
          <Button onClick={submit} disabled={create.isPending || link.isPending}>
            <Plus className="h-4 w-4" />
            Link parent
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  onChange,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function CheckboxRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-saffron"
      />
      {label}
    </label>
  );
}
