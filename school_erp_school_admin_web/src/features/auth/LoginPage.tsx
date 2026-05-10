import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login as loginApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

const SCHOOL_ROLES = new Set([
  "school_admin",
  "principal",
  "vice_principal",
  "coordinator",
  "class_teacher",
  "subject_teacher",
  "accountant",
  "librarian",
  "transport_manager",
  "hostel_warden",
  "office_staff",
]);

function detectSubdomain(): string {
  const fromQuery = new URLSearchParams(window.location.search).get("school");
  if (fromQuery) return fromQuery.toLowerCase();
  const host = window.location.host.split(":")[0];
  const parts = host.split(".");
  if (parts.length >= 3 && !["www", "admin", "api"].includes(parts[0])) return parts[0];
  return "demo";
}

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const subdomain = detectSubdomain();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginApi({ identifier, password, subdomain });
      const allowed = res.user.roles.some((r) => SCHOOL_ROLES.has(r));
      if (!allowed) {
        setError("This console is for school staff. Use the mobile app to sign in as parent/student.");
        setSubmitting(false);
        return;
      }
      setSession(res.user, res.tokens);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not sign in. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid min-h-full grid-cols-1 lg:grid-cols-[1fr_minmax(420px,440px)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-saffron p-12 text-warm-white lg:flex">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.4em] text-marigold-pale">
            {subdomain}.jaikalki.com
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
              Signing in to <span className="font-mono text-saffron-dark">{subdomain}.jaikalki.com</span>.
              Demo seed: <span className="font-mono text-saffron-dark">admin@demo.school / School@123</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
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
              <p className="text-center text-xs text-muted-foreground">
                Wrong school?{" "}
                <a href={`?school=${subdomain}`} className="font-medium text-saffron-dark">
                  switch with ?school=…
                </a>
              </p>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
