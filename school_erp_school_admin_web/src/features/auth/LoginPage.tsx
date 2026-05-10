import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/stores/auth";

function detectSubdomain(): string {
  const host = window.location.host.split(":")[0];
  const parts = host.split(".");
  if (parts.length >= 3) return parts[0];
  return "demo";
}

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const subdomain = detectSubdomain();

  // Phase 0 stub. Phase 2 wires this to /v1/auth/login + tenant resolution.
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSession(
      {
        id: 1,
        name: "School Admin",
        email,
        roles: ["school_admin"],
        tenant_id: 1,
        tenant_subdomain: subdomain,
        school_name: "Sample School",
      },
      "phase0-stub-token",
    );
    setSubmitting(false);
    navigate("/dashboard");
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
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-marigold/40 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-teal/40 blur-3xl"
        />
      </aside>

      <main className="flex items-center justify-center bg-warm-white p-6">
        <Card className="w-full max-w-md border-saffron-pale">
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>
              Sign in as the school admin for{" "}
              <span className="font-mono text-saffron-dark">{subdomain}.jaikalki.com</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email or Mobile</Label>
                <Input
                  id="email"
                  required
                  placeholder="admin@yourschool.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Phase 0 stub · real auth + multi-role lands in Phase 2
              </p>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
