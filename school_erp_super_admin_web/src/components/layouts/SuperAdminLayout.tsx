import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Building2,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  ScrollText,
  Settings,
  Users2,
  Wallet,
  X,
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

const SIDEBAR_KEY = "jaikalki.superadmin.sidebar.collapsed";

export function SuperAdminLayout() {
  const user = useAuth((s) => s.user);
  const tokens = useAuth((s) => s.tokens);
  const clear = useAuth((s) => s.clear);
  const navigate = useNavigate();
  const location = useLocation();

  // Desktop: ☰ switches between the full menu and an icon rail, remembered
  // per browser (storage may be unavailable, eg. private mode).
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "1";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
    } catch {
      // not persisted; fine
    }
  }, [collapsed]);

  // Phone: ☰ opens a drawer, which closes again on navigation.
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const onMenuButton = () => {
    if (window.matchMedia("(max-width: 767px)").matches) setMobileOpen(true);
    else setCollapsed((c) => !c);
  };

  const onLogout = async () => {
    try {
      await logoutApi(tokens?.refresh_token);
    } catch {
      // best-effort - we still clear local state
    }
    clear();
    navigate("/login", { replace: true });
  };

  // Page name for the top bar (/schools/12 → Organizations).
  const current = nav.find(
    (n) => location.pathname === n.to || location.pathname.startsWith(n.to + "/"),
  );

  const fullBody = (
    <>
      <div className="mb-8 flex items-center gap-3">
        <img src="/favicon-192.png" alt="" className="h-11 w-11 shrink-0 rounded-xl shadow" />
        <div>
          <p className="font-display text-lg font-semibold text-indigo-dark">Jaikalki</p>
          <p className="text-xs uppercase tracking-[0.2em] text-saffron-dark">Super Admin</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
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
    </>
  );

  const railItem = (active: boolean) =>
    cn(
      "flex h-11 w-11 items-center justify-center rounded-xl transition-colors",
      active
        ? "bg-saffron-pale text-saffron-darker"
        : "text-indigo/70 hover:bg-saffron-pale/60 hover:text-indigo-dark",
    );

  const railBody = (
    <>
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        title="Open menu"
        className="mb-6 flex flex-col items-center gap-2 rounded-lg px-1 py-1 hover:bg-saffron-pale/40"
      >
        <img src="/favicon-192.png" alt="" className="h-11 w-11 rounded-xl shadow" />
        <span className="text-center font-display text-[11px] font-semibold leading-tight text-indigo-dark">
          Jaikalki
          <span className="block text-[9px] font-sans uppercase tracking-[0.14em] text-saffron-dark">
            Super Admin
          </span>
        </span>
      </button>

      <nav aria-label="Main" className="flex flex-1 flex-col items-center gap-2 overflow-y-auto [scrollbar-width:none]">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            aria-label={label}
            className={({ isActive }) => railItem(isActive)}
          >
            <Icon className="h-5 w-5" />
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        onClick={onLogout}
        title="Sign out"
        aria-label="Sign out"
        className={cn(railItem(false), "mt-3")}
      >
        <LogOut className="h-5 w-5" />
      </button>
    </>
  );

  return (
    <div className="flex h-full flex-col bg-ivory md:flex-row">
      {/* Desktop sidebar: full menu or (☰) icon rail. Inner width is fixed
          so content doesn't reflow while the width animates. */}
      <aside
        id="super-admin-sidebar"
        className={cn(
          "hidden h-full shrink-0 overflow-hidden border-r border-saffron-pale bg-warm-white transition-[width] duration-200 ease-out motion-reduce:transition-none md:block",
          collapsed ? "md:w-[96px]" : "md:w-[260px]",
        )}
      >
        {collapsed ? (
          <div className="flex h-full w-[96px] flex-col items-center px-2 py-7">{railBody}</div>
        ) : (
          <div className="flex h-full w-[260px] flex-col px-5 py-7">{fullBody}</div>
        )}
      </aside>

      {/* Phone drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85%] flex-col border-r border-saffron-pale bg-warm-white px-5 py-5 transition-transform md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="mb-3 flex justify-end">
          <button
            type="button"
            className="rounded-md p-2 text-muted-foreground hover:bg-muted"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {fullBody}
      </aside>

      {/* Content column: the top bar sits outside the scrolling <main>,
          so it stays pinned while the page scrolls. */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-saffron-pale bg-warm-white px-3 md:px-6">
          <button
            type="button"
            className="rounded-md p-2 text-indigo-dark hover:bg-saffron-pale/60"
            onClick={onMenuButton}
            aria-label="Toggle menu"
            aria-controls="super-admin-sidebar"
            title={collapsed ? "Show menu" : "Hide menu"}
          >
            <Menu className="h-5 w-5" />
          </button>
          <p className="min-w-0 truncate text-sm font-semibold text-indigo-dark">
            {current?.label ?? "Super Admin"}
          </p>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto px-4 py-4 md:px-10 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
