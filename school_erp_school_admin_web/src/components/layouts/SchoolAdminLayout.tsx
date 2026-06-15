import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  Building,
  BarChart3,
  Bus,
  CalendarDays,
  ClipboardList,
  CreditCard,
  GraduationCap,
  Home,
  KeyRound,
  Layers,
  FileText,
  Library,
  LogOut,
  MessageCircle,
  Receipt,
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
  { to: "/users", label: "Users & logins", icon: KeyRound },
  { to: "/attendance", label: "Attendance", icon: ClipboardList },
  { to: "/timetable", label: "Timetable", icon: CalendarDays },
  { to: "/homework", label: "Homework", icon: ClipboardList },
  { to: "/exams", label: "Exams", icon: BookOpenCheck },
  { to: "/report-cards", label: "Report cards", icon: FileText },
  { to: "/fees", label: "Fees", icon: Receipt },
  { to: "/communication", label: "Communication", icon: MessageCircle },
  { to: "/library", label: "Library", icon: Library },
  { to: "/transport", label: "Transport", icon: Bus },
  { to: "/hostel", label: "Hostel", icon: Building },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/subscription", label: "Subscription", icon: CreditCard },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function SchoolAdminLayout() {
  const user = useAuth((s) => s.user);
  const tokens = useAuth((s) => s.tokens);
  const clear = useAuth((s) => s.clear);
  const navigate = useNavigate();

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
