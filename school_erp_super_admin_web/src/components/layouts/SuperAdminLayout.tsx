import { NavLink, Outlet } from "react-router-dom";
import { Building2, Gauge, Receipt, Settings, ShieldCheck, Users2 } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Overview", icon: Gauge },
  { to: "/schools", label: "Schools", icon: Building2 },
  { to: "/plans", label: "Plans & Billing", icon: Receipt },
  { to: "/staff", label: "Platform Staff", icon: Users2 },
  { to: "/audit", label: "Audit & Security", icon: ShieldCheck },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function SuperAdminLayout() {
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

        <p className="mt-6 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          v0.1.0 · Phase 0 foundation
        </p>
      </aside>

      <main className="overflow-y-auto px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
