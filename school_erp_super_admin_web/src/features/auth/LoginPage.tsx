import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/stores/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Phase 0: stub login — Phase 2 hooks this up to /v1/auth/login.
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSession(
      {
        id: 1,
        name: "Jaikalki Super Admin",
        email,
        roles: ["super_admin"],
        tenant_id: null,
        tenant_subdomain: null,
      },
      "phase0-stub-token",
    );
    setSubmitting(false);
    navigate("/dashboard");
  };

  return (
    <div className="grid min-h-full grid-cols-1 lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-indigo-dark p-12 text-warm-white lg:flex">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.4em] text-marigold">
            Jaikalki Technology
          </p>
          <h1 className="mt-6 font-display text-4xl leading-tight text-warm-white">
            School operations <em className="italic text-saffron-light">in saffron, gold, and teal.</em>
          </h1>
          <p className="mt-4 max-w-md text-sm text-marigold-pale/90">
            Multi-tenant SaaS for Indian schools. Onboard a campus, configure a plan, and watch the
            mobile-first experience light up across roles.
          </p>
        </div>
        <div className="font-hindi text-2xl text-marigold">
          सरस्वती को नमन — जहाँ ज्ञान, वहीं विकास
        </div>
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-saffron/40 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-teal/40 blur-3xl"
        />
      </aside>

      <main className="flex items-center justify-center bg-warm-white p-6">
        <Card className="w-full max-w-md border-saffron-pale">
          <CardHeader>
            <CardTitle>Super Admin Console</CardTitle>
            <CardDescription>Sign in to manage the Jaikalki School ERP platform.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  placeholder="admin@jaikalki.com"
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
                {submitting ? "Signing in…" : "Continue"}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Phase 0 stub · real auth lands in Phase 2
              </p>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
