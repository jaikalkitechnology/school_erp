import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BookOpen,
  BookOpenCheck,
  Building,
  BarChart3,
  Bus,
  CalendarDays,
  ClipboardList,
  CalendarCheck,
  CreditCard,
  GraduationCap,
  Hand,
  Home,
  KeyRound,
  Layers,
  FileText,
  Library,
  LogOut,
  MessageCircle,
  Receipt,
  ReceiptText,
  RotateCcw,
  Settings,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { logout as logoutApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

const nav = [
  { to: "/dashboard", label: "Overview", icon: Home },
  { to: "/org", label: "Departments / Classes", icon: Layers },
  { to: "/academic", label: "Academic year", icon: CalendarDays },
  { to: "/curriculum", label: "Curriculum", icon: BookOpenCheck },
  { to: "/students", label: "Students", icon: GraduationCap },
  { to: "/teachers", label: "Teachers", icon: Users },
  { to: "/staff", label: "Staff attendance", icon: CalendarCheck },
  { to: "/users", label: "Users & logins", icon: KeyRound },
  { to: "/attendance", label: "Attendance", icon: ClipboardList },
  { to: "/timetable", label: "Timetable", icon: CalendarDays },
  { to: "/homework", label: "Homework", icon: ClipboardList },
  { to: "/exams", label: "Exams", icon: BookOpenCheck },
  { to: "/report-cards", label: "Report cards", icon: FileText },
  { to: "/fees", label: "Fees", icon: Receipt },
  { to: "/communication", label: "Communication", icon: MessageCircle },
  // ---- Library ---------------------------------------------------
  // Each sub-section gets its own sidebar entry so it can be granted
  // individually on the Users & credentials Page access checklist.
  // A librarian can be given just Books + Issue + Return, or the
  // full set, without spilling into unrelated modules.
  { to: "/library", label: "Library dashboard", icon: Library },
  { to: "/library-books", label: "Books", icon: BookOpen },
  { to: "/library-categories", label: "Categories", icon: Layers },
  { to: "/library-issue", label: "Issue books", icon: Hand },
  { to: "/library-return", label: "Return books", icon: RotateCcw },
  { to: "/library-fines", label: "Fine management", icon: ReceiptText },
  { to: "/library-reports", label: "Library reports", icon: BarChart3 },
  { to: "/transport", label: "Transport", icon: Bus },
  { to: "/hostel", label: "Hostel", icon: Building },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/subscription", label: "Subscription", icon: CreditCard },
  { to: "/settings", label: "Settings", icon: Settings },
];

// Senior leadership sees every page without needing per-page grants.
// Keep in sync with the backend role catalogue.
const FULL_ACCESS_ROLES = new Set([
  "school_admin",
  "super_admin",
  "principal",
  "vice_principal",
  "management",
]);

/**
 * Role-scoped sidebar. Every entry is checked against the user's
 * ``granted_admin_pages`` — so a librarian only sees the Library
 * sub-pages that were granted to them via Users & credentials, a
 * receptionist only sees the reception surfaces, and so on. Senior
 * leadership bypasses the gate and sees everything.
 *
 * The slug in ``granted_admin_pages`` matches the sidebar route path
 * with the leading slash stripped ("library-books" for "/library-books").
 */
function useFilteredNav(roles: string[], granted: string[]) {
  const bypass = roles.some((r) => FULL_ACCESS_ROLES.has(r));
  if (bypass) return nav;
  const granted_slugs = new Set(
    granted.map((s) => (s.startsWith("/") ? s.slice(1) : s)),
  );
  return nav.filter((n) => granted_slugs.has(n.to.replace(/^\//, "")));
}

export function SchoolAdminLayout() {
  const user = useAuth((s) => s.user);
  const tokens = useAuth((s) => s.tokens);
  const clear = useAuth((s) => s.clear);
  const navigate = useNavigate();
  const visibleNav = useFilteredNav(
    user?.roles ?? [],
    user?.granted_admin_pages ?? [],
  );

  const onLogout = async () => {
    try {
      await logoutApi(tokens?.refresh_token);
    } catch {
      // best-effort
    }
    clear();
    navigate("/login", { replace: true });
  };

  return (
    <div className="grid h-full grid-cols-[260px_1fr] bg-ivory">
      <aside className="flex h-full flex-col border-r border-saffron-pale bg-warm-white px-5 py-7">
        <div className="mb-6">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-saffron-dark">
            {user?.tenant_subdomain ?? "your-school"}.jaikalki.com
          </p>
          <p className="mt-1 font-display text-lg font-semibold text-indigo-dark">
            {user?.school_name ?? "School Admin"}
          </p>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
          {visibleNav.length === 0 && (
            <p className="rounded-md bg-marigold-pale/40 px-3 py-2 text-xs text-marigold-dark">
              You don't have any admin pages assigned yet. Please use the
              mobile app, or ask your school admin to grant page access.
            </p>
          )}
          {visibleNav.map(({ to, label, icon: Icon }) => (
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
              <p className="truncate">{user.primary_role?.replace(/_/g, " ") ?? "Staff"}</p>
            </div>
          )}
          <Button variant="ghost" size="sm" className="w-full justify-start" onClick={onLogout}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Powered by Jaikalki · v0.1.0
          </p>
        </div>
      </aside>

      <main className="overflow-y-auto px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
