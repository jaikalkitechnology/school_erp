import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  KeyRound, Pencil, Plus, Power, Search, Trash2, UserCheck, UserX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  activateUser,
  createAdminUser,
  deactivateUser,
  deleteAdminUser,
  listAdminUsers,
  listAssignableRoles,
  setUserPassword,
  updateAdminUser,
  type RoleOption,
  type UserRow,
} from "./api";

export function UsersPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [roleCode, setRoleCode] = useState("");
  const [onlyActive, setOnlyActive] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const params = {
    q: q || undefined,
    role_code: roleCode || undefined,
    only_active: onlyActive || undefined,
    limit,
    offset,
  };
  const list = useQuery({ queryKey: ["admin-users", params], queryFn: () => listAdminUsers(params) });
  const roles = useQuery({ queryKey: ["admin-user-roles"], queryFn: listAssignableRoles });

  const roleMap = useMemo(
    () => new Map((roles.data ?? []).map((r) => [r.code, r.name])),
    [roles.data],
  );

  const total = list.data?.total ?? 0;
  const showingTo = Math.min(offset + limit, total);

  const [editing, setEditing] = useState<UserRow | null>(null);
  const [creating, setCreating] = useState(false);
  const [pwTarget, setPwTarget] = useState<UserRow | null>(null);
  const [opError, setOpError] = useState<string | null>(null);

  const toggleMut = useMutation({
    mutationFn: (u: UserRow) => (u.is_active ? deactivateUser(u.id) : activateUser(u.id)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (e: any) => setOpError(e?.response?.data?.detail ?? "Could not toggle"),
  });

  const removeMut = useMutation({
    mutationFn: (id: number) => deleteAdminUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (e: any) => setOpError(e?.response?.data?.detail ?? "Could not delete"),
  });

  const onDelete = (u: UserRow) => {
    setOpError(null);
    const ok = window.confirm(
      `Delete login for ${u.full_name}?\n\n` +
        "This removes the user account permanently. Role-specific records " +
        "(Teacher, Parent, Student) won't be touched.",
    );
    if (ok) removeMut.mutate(u.id);
  };

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">Logins</p>
          <h1 className="mt-1 font-display text-4xl text-indigo-dark">Users &amp; credentials</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Manage logins for support staff — vice principal, coordinators,
            class teachers, accountants, librarians, transport managers,
            hostel wardens, bus staff, area supervisors and visitor-desk
            operators. Teachers and parents are onboarded from the Teachers
            and Students screens; principal and office staff via Teachers
            &rarr; Onboard. Create accounts, reset passwords, activate or
            deactivate.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" />
          Add user
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>Search by name, email, or phone. Filter by role.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => { setQ(e.target.value); setOffset(0); }}
                placeholder="Name / email / phone"
                className="pl-9"
              />
            </div>
            <select
              className="h-11 rounded-md border border-input bg-background px-3 text-sm"
              value={roleCode}
              onChange={(e) => { setRoleCode(e.target.value); setOffset(0); }}
            >
              <option value="">All roles</option>
              {(roles.data ?? []).map((r) => (
                <option key={r.code} value={r.code}>{r.name}</option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                checked={onlyActive}
                onChange={(e) => { setOnlyActive(e.target.checked); setOffset(0); }}
              />
              Active only
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {total} {total === 1 ? "user" : "users"}
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {total > 0 && `showing ${offset + 1}–${showingTo}`}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
          ) : list.isError ? (
            <p className="px-6 py-4 text-sm text-destructive">Could not load users.</p>
          ) : !list.data?.items.length ? (
            <p className="px-6 py-4 text-sm text-muted-foreground">No users match.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y bg-muted/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-6 py-3">User</th>
                    <th className="px-4 py-3">Contact</th>
                    <th className="px-4 py-3">Roles</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Last login</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((u) => (
                    <tr key={u.id} className="border-b last:border-b-0 hover:bg-saffron-pale/30">
                      <td className="px-6 py-3">
                        <p className="font-medium text-indigo-dark">{u.full_name}</p>
                        <p className="font-mono text-[11px] text-muted-foreground">#{u.id}</p>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {u.email && <div>{u.email}</div>}
                        {u.phone && <div className="font-mono">{u.phone}</div>}
                        {!u.email && !u.phone && "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {u.role_codes.length ? u.role_codes.map((c) => (
                            <span
                              key={c}
                              className="rounded-full bg-saffron-pale/60 px-2 py-0.5 text-[11px] font-medium text-saffron-darker"
                              title={c}
                            >
                              {roleMap.get(c) ?? c}
                            </span>
                          )) : <span className="text-xs text-muted-foreground">—</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
                            u.is_active
                              ? "bg-teal-pale text-teal-dark"
                              : "bg-muted text-muted-foreground",
                          )}
                        >
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost" size="icon" title="Edit"
                            onClick={() => setEditing(u)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost" size="icon" title="Set password"
                            onClick={() => setPwTarget(u)}
                          >
                            <KeyRound className="h-4 w-4 text-saffron-dark" />
                          </Button>
                          <Button
                            variant="ghost" size="icon"
                            title={u.is_active ? "Deactivate" : "Activate"}
                            disabled={toggleMut.isPending}
                            onClick={() => { setOpError(null); toggleMut.mutate(u); }}
                          >
                            {u.is_active
                              ? <UserX className="h-4 w-4 text-marigold-dark" />
                              : <UserCheck className="h-4 w-4 text-teal-dark" />}
                          </Button>
                          <Button
                            variant="ghost" size="icon" title="Delete"
                            disabled={removeMut.isPending}
                            onClick={() => onDelete(u)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {opError && (
                <p className="border-t bg-destructive/10 px-6 py-2 text-xs text-destructive">
                  {opError}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {total > limit && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Previous
          </Button>
          <Button variant="outline" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            Next
          </Button>
        </div>
      )}

      {creating && (
        <CreateOrEditDialog
          mode="create"
          roles={roles.data ?? []}
          onClose={() => setCreating(false)}
        />
      )}
      {editing && (
        <CreateOrEditDialog
          mode="edit"
          user={editing}
          roles={roles.data ?? []}
          onClose={() => setEditing(null)}
        />
      )}
      {pwTarget && (
        <SetPasswordDialog
          user={pwTarget}
          onClose={() => setPwTarget(null)}
        />
      )}
    </div>
  );
}

// ---- Create / edit dialog -------------------------------------------------

function CreateOrEditDialog({
  mode, user, roles, onClose,
}: {
  mode: "create" | "edit";
  user?: UserRow;
  roles: RoleOption[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [password, setPassword] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user?.role_codes ?? []);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => createAdminUser({
      full_name: fullName,
      email: email || undefined,
      phone: phone || undefined,
      password,
      role_codes: selectedRoles,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Could not save"),
  });

  const update = useMutation({
    mutationFn: () => updateAdminUser(user!.id, {
      full_name: fullName,
      email: email || undefined,
      phone: phone || undefined,
      role_codes: selectedRoles,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Could not save"),
  });

  const canSubmit = fullName.length >= 1 && selectedRoles.length > 0
    && (mode === "edit" || password.length >= 6);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-background p-6 shadow-2xl">
        <h2 className="font-display text-2xl text-indigo-dark">
          {mode === "create" ? "Add user" : `Edit ${user!.full_name}`}
        </h2>
        <p className="text-xs text-muted-foreground">
          {mode === "create" ? "Creates a login and assigns one or more roles." : `User #${user!.id}`}
        </p>

        <div className="mt-4 space-y-3">
          <Field label="Full name *" value={fullName} onChange={setFullName} />
          <Field label="Email" value={email} onChange={setEmail} type="email" />
          <Field label="Phone" value={phone} onChange={setPhone} />
          {mode === "create" && (
            <Field label="Password *" value={password} onChange={setPassword} type="password" hint="At least 6 characters." />
          )}
          <div className="space-y-1.5">
            <Label>Roles *</Label>
            <div className="grid max-h-44 grid-cols-2 gap-1 overflow-y-auto rounded-md border border-input p-2">
              {roles.map((r) => {
                const on = selectedRoles.includes(r.code);
                return (
                  <label
                    key={r.code}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-saffron-pale/40",
                      on && "bg-saffron-pale/60",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={(e) =>
                        setSelectedRoles((s) =>
                          e.target.checked ? [...s, r.code] : s.filter((c) => c !== r.code),
                        )
                      }
                    />
                    {r.name}
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            disabled={!canSubmit || create.isPending || update.isPending}
            onClick={() => { setError(null); mode === "create" ? create.mutate() : update.mutate(); }}
          >
            {(create.isPending || update.isPending) ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---- Set password dialog --------------------------------------------------

function SetPasswordDialog({ user, onClose }: { user: UserRow; onClose: () => void }) {
  const qc = useQueryClient();
  const [pw, setPw] = useState(suggestPassword());
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => setUserPassword(user.id, pw),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Could not set password"),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md rounded-xl bg-background p-6 shadow-2xl">
        <h2 className="flex items-center gap-2 font-display text-2xl text-indigo-dark">
          <KeyRound className="h-5 w-5 text-saffron" /> Set password
        </h2>
        <p className="text-xs text-muted-foreground">{user.full_name} (#{user.id})</p>

        <div className="mt-4 space-y-2">
          <Label>New password</Label>
          <div className="flex gap-2">
            <Input value={pw} onChange={(e) => setPw(e.target.value)} />
            <Button variant="outline" type="button" onClick={() => setPw(suggestPassword())}>
              <Power className="h-4 w-4" />
              Regenerate
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Tell the user this password once — they should change it on first login.
          </p>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            disabled={pw.length < 6 || save.isPending}
            onClick={() => { setError(null); save.mutate(); }}
          >
            {save.isPending ? "Saving…" : "Set password"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, value, onChange, hint, type = "text",
}: {
  label: string; value: string; onChange: (v: string) => void; hint?: string; type?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function suggestPassword(): string {
  // Memorable but unique: two short words + 3 digits. Not for high-security
  // accounts — it's a temporary password the admin reads out to the user.
  const a = ["sun", "moon", "raj", "veda", "lotus", "amla", "ganga", "tulsi"];
  const b = ["bird", "fox", "deer", "lion", "tiger", "peacock", "owl"];
  const pick = (arr: string[]) => arr[Math.floor(Math.random() * arr.length)];
  const n = Math.floor(100 + Math.random() * 900);
  return `${pick(a)}-${pick(b)}-${n}`;
}
