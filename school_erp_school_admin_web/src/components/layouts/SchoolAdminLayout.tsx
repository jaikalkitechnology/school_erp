import { NavLink, Outlet } from "react-router-dom";
import {
  BookOpenCheck,
  Bus,
  CalendarDays,
  ClipboardList,
  GraduationCap,
  Home,
  Library,
  MessageCircle,
  Receipt,
  Settings,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/stores/auth";

const nav = [
  { to: "/dashboard", label: "Overview", icon: Home },
  { to: "/students", label: "Students", icon: GraduationCap },
  { to: "/teachers", label: "Teachers", icon: Users },
  { to: "/attendance", label: "Attendance", icon: ClipboardList },
  { to: "/timetable", label: "Timetable", icon: CalendarDays },
  { to: "/exams", label: "Exams", icon: BookOpenCheck },
  { to: "/fees", label: "Fees", icon: Receipt },
  { to: "/communication", label: "Communication", icon: MessageCircle },
  { to: "/library", label: "Library", icon: Library },
  { to: "/transport", label: "Transport", icon: Bus },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function SchoolAdminLayout() {
  const user = useAuth((s) => s.user);

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

        <p className="mt-6 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Powered by Jaikalki · v0.1.0
        </p>
      </aside>

      <main className="overflow-y-auto px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
