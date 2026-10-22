import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, KeyRound, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listSchoolAdmins, setSchoolAdmin } from "./api";
import { AdminLoginFields, EMPTY_ADMIN_LOGIN, adminLoginValid, type AdminLoginForm } from "./AdminLoginFields";
import type { Tenant } from "./types";

function errorText(err: unknown) {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" && detail !== "Validation error" ? detail : "Could not save the login. Try again.";
}

/** Shows the school's admin login(s) and lets the super admin set one:
 *  a new email creates a login, an existing one gets a new password. */
export function AdminLoginCard({ tenant }: { tenant: Tenant }) {
  const qc = useQueryClient();
  const admins = useQuery({ queryKey: ["tenant-admins", tenant.id], queryFn: () => listSchoolAdmins(tenant.id) });
  const [form, setForm] = useState<AdminLoginForm>(EMPTY_ADMIN_LOGIN);
  const [tried, setTried] = useState(false);
  const [savedEmail, setSavedEmail] = useState<string | null>(null);
  // Bumped after a save so the cleared password boxes start untouched.
  const [round, setRound] = useState(0);

  // Start from the current admin so "reset password" is one step.
  const first = admins.data?.[0];
  useEffect(() => {
    if (first) setForm((f) => (f.email ? f : { ...f, full_name: first.full_name, email: first.email ?? "" }));
  }, [first]);

  const save = useMutation({
    mutationFn: () =>
      setSchoolAdmin(tenant.id, {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      }),
    onSuccess: (user) => {
      setSavedEmail(user.email);
      setForm((f) => ({ ...f, password: "", confirm: "" }));
      setTried(false);
      setRound((r) => r + 1);
      qc.invalidateQueries({ queryKey: ["tenant-admins", tenant.id] });
    },
  });

  const email = form.email.trim().toLowerCase();
  const existing = admins.data?.some((a) => a.email === email);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-saffron-dark" />
          School admin login
        </CardTitle>
        <CardDescription>
          Signs in to the school admin panel with School <code className="font-mono">{tenant.subdomain}</code>.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {admins.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : admins.data && admins.data.length > 0 ? (
          <ul className="divide-y divide-saffron-pale rounded-md border border-saffron-pale">
            {admins.data.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                <UserRound className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-indigo-dark">{a.full_name}</span>
                <span className="font-mono text-xs text-muted-foreground">{a.email}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {a.is_active ? "" : "Inactive · "}
                  {a.last_login_at ? `Last sign-in ${new Date(a.last_login_at).toLocaleDateString()}` : "Never signed in"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-md border border-dashed border-marigold bg-marigold-pale/40 px-4 py-3 text-sm text-indigo-dark">
            This school has no admin login yet, so nobody can sign in to its admin panel. Set one below.
          </p>
        )}

        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setTried(true);
            setSavedEmail(null);
            if (adminLoginValid(form)) save.mutate();
          }}
        >
          <AdminLoginFields key={round} idPrefix={`admin-${tenant.id}`} value={form} onChange={setForm} showAll={tried} />
          {save.isError && <p className="text-sm text-destructive">{errorText(save.error)}</p>}
          {savedEmail && (
            <p className="flex items-center gap-2 text-sm text-teal-dark">
              <CheckCircle2 className="h-4 w-4" />
              Saved. {savedEmail} can sign in with the new password.
            </p>
          )}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : existing ? "Reset password" : "Create admin login"}
            </Button>
            <p className="text-xs text-muted-foreground">
              {existing
                ? "This email already has a login; saving sets its new name and password."
                : "A new login is created with the school admin role."}
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
