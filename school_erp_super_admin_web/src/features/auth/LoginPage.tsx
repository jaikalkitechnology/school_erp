import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login as loginApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginApi({ identifier, password, subdomain: "platform" });
      if (!res.user.roles.includes("super_admin")) {
        setError("This console is for Jaikalki super admins only.");
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
            Multi-tenant SaaS for Indian schools. Onboard a campus, configure a plan, watch the
            mobile-first experience light up across roles.
          </p>
        </div>
        <div className="font-hindi text-2xl text-marigold">
          सरस्वती को नमन — जहाँ ज्ञान, वहीं विकास
        </div>
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-saffron/40 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-teal/40 blur-3xl" />
      </aside>

      <main className="flex items-center justify-center bg-warm-white p-6">
        <Card className="w-full max-w-md border-saffron-pale">
          <CardHeader>
            <CardTitle>Super Admin Console</CardTitle>
            <CardDescription>
              Sign in with your Jaikalki staff account. Default seed:{" "}
              <span className="font-mono text-saffron-dark">admin@jaikalki.com / Admin@123</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="identifier">Email or phone</Label>
                <Input
                  id="identifier"
                  required
                  autoComplete="username"
                  placeholder="admin@jaikalki.com"
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
                {submitting ? "Signing in…" : "Continue"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
