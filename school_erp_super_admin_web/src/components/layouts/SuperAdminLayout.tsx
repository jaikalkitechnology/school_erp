import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Building2,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Megaphone,
  ScrollText,
  Settings,
  Users2,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { logout as logoutApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/schools", label: "Organizations", icon: Building2 },
  { to: "/plans", label: "Plans", icon: CreditCard },
  { to: "/billing", label: "Billing", icon: Wallet },
  { to: "/staff", label: "Staff", icon: Users2 },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/announcements", label: "Announcements", icon: Megaphone },
  { to: "/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function SuperAdminLayout() {
  const user = useAuth((s) => s.user);
  const tokens = useAuth((s) => s.tokens);
  const clear = useAuth((s) => s.clear);
  const navigate = useNavigate();

  const onLogout = async () => {
    try {
      await logoutApi(tokens?.refresh_token);
    } catch {
      // best-effort - we still clear local state
    }
    clear();
    navigate("/login", { replace: true });
  };

  return (
    <div className="grid h-full grid-cols-[260px_1fr] bg-ivory">
      <aside className="flex h-full flex-col border-r border-saffron-pale bg-warm-white px-5 py-7">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-saffron text-warm-white font-display text-lg font-semibold shadow">
            J
          </div>
          <div>
            <p className="font-display text-lg font-semibold text-indigo-dark">Jaikalki</p>
            <p className="text-xs uppercase tracking-[0.2em] text-saffron-dark">Super Admin</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-saffron-pale text-saffron-darker"
                    : "text-indigo/80 hover:bg-saffron-pale/60 hover:text-indigo-dark",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6 space-y-3 border-t border-saffron-pale pt-4">
          {user && (
            <div className="text-xs text-muted-foreground">
              <p className="font-medium text-indigo-dark">{user.full_name}</p>
              <p className="truncate">{user.email}</p>
            </div>
          )}
          <Button variant="ghost" size="sm" className="w-full justify-start" onClick={onLogout}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">v0.1.0 · Phase 2</p>
        </div>
      </aside>

      <main className="overflow-y-auto px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
