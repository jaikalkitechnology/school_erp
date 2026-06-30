import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login as loginApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

// Mirrors the backend ADMIN_PANEL_ROLES matrix in
// app/services/auth.py. The backend is the source of truth — a
// rejected role gets a 403 with the canonical error message — but we
// keep this client-side allow list so a server with role bypass
// (unset platform field) doesn't accidentally drop a parent / student
// into the admin web.
const SCHOOL_ROLES = new Set([
  "school_admin", "super_admin", "supervisor",
  "management", "principal", "vice_principal", "hod",
  "office_admin", "office_staff", "receptionist", "visitor_desk",
  "class_teacher", "subject_teacher", "coordinator", "teacher",
  "librarian", "transport_manager", "hostel_warden",
  "accountant", "accounts", "payroll", "data_entry_operator",
]);

// Hosts that serve the school admin web itself rather than a per-tenant
// subdomain. When the user lands on one of these, we don't try to read a
// subdomain from the URL — they pick / type one on the form.
const APP_HOST_LABELS = new Set(["www", "admin", "api", "school", "campus", "app"]);

function detectSubdomain(): string | null {
  // Explicit override always wins.
  const fromQuery = new URLSearchParams(window.location.search).get("school");
  if (fromQuery) return fromQuery.toLowerCase();
  // Last-used subdomain (sticky between sessions).
  const stored = localStorage.getItem("jaikalki.subdomain");
  if (stored) return stored;
  // Hostname-derived: requires at least 3 labels (e.g. demo.school.jaikalki.in)
  // and the first label must not be an app-host marker.
  const host = window.location.host.split(":")[0];
  const parts = host.split(".");
  if (parts.length < 3) return null;
  if (APP_HOST_LABELS.has(parts[0])) return null;
  return parts[0];
}

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const [subdomain, setSubdomain] = useState<string>(detectSubdomain() ?? "demo");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!subdomain.trim()) {
      setError("Pick the school's subdomain (e.g. demo).");
      return;
    }
    setSubmitting(true);
    try {
      const cleanSubdomain = subdomain.trim().toLowerCase();
      // Don't persist subdomain until the login actually succeeds, otherwise
      // a typo poisons localStorage and we keep submitting the wrong tenant
      // on every reload. loginApi sends the subdomain as an explicit header
      // for this call; the auth store writes it to localStorage on success.
      const res = await loginApi({ identifier, password, subdomain: cleanSubdomain });
      const allowed = res.user.roles.some((r) => SCHOOL_ROLES.has(r));
      if (!allowed) {
        setError("You are not authorized to access the Admin Panel.");
        setSubmitting(false);
        return;
      }
      localStorage.setItem("jaikalki.subdomain", cleanSubdomain);
      setSession(res.user, res.tokens);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not sign in. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  // Pretty FQDN for the wallpaper text — falls back to current hostname.
  const baseDomain = (() => {
    const host = window.location.host.split(":")[0];
    const parts = host.split(".");
    if (parts.length >= 2) return parts.slice(-2).join(".");
    return host;
  })();
  const fqdn = `${subdomain || "<school>"}.${baseDomain}`;

  return (
    <div className="grid min-h-full grid-cols-1 lg:grid-cols-[1fr_minmax(420px,440px)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-saffron p-12 text-warm-white lg:flex">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.4em] text-marigold-pale">
            {fqdn}
          </p>
          <h1 className="mt-6 font-display text-4xl leading-tight text-warm-white">
            Run your school <em className="italic text-marigold">like a Monday morning assembly.</em>
          </h1>
          <p className="mt-4 max-w-md text-sm text-marigold-pale/95">
            Attendance, fees, exams, transport — every module lives behind one school admin login.
            This is your console.
          </p>
        </div>
        <div className="font-hindi text-2xl text-marigold-pale">
          विद्या ददाति विनयम् · विनयाद् याति पात्रताम्
        </div>
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-marigold/40 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-teal/40 blur-3xl" />
      </aside>

      <main className="flex items-center justify-center bg-warm-white p-6">
        <Card className="w-full max-w-md border-saffron-pale">
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>
              Signing in to <span className="font-mono text-saffron-dark">{fqdn}</span>.
              Demo seed: <span className="font-mono text-saffron-dark">admin@demo.school / School@123</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="subdomain">School</Label>
                <Input
                  id="subdomain"
                  required
                  placeholder="demo"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="identifier">Email or mobile</Label>
                <Input
                  id="identifier"
                  required
                  autoComplete="username"
                  placeholder="admin@demo.school"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
