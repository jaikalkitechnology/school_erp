import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AlertOctagon,
  ArrowUpDown,
  Bell,
  BookOpen,
  BookOpenCheck,
  Building,
  BarChart3,
  Bus,
  CalendarDays,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  CalendarCheck,
  Clock,
  Copy,
  CreditCard,
  GraduationCap,
  Hand,
  History,
  Home,
  KeyRound,
  Layers,
  FileText,
  Library,
  LogOut,
  Menu,
  MessageCircle,
  PenTool,
  Printer,
  Receipt,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Send,
  Settings,
  ShieldCheck,
  Users,
  Warehouse,
  X,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { logout as logoutApi } from "@/lib/auth-api";
import { useAuth } from "@/stores/auth";

// ---- Nav model -----------------------------------------------------------
// A nav item is either a leaf (has a route) or a group (renders as a
// collapsible header + children). Groups themselves aren't routes —
// clicking the header just toggles the section open / closed.
interface NavLeaf {
  kind: "leaf";
  to: string;
  label: string;
  icon: LucideIcon;
}
interface NavGroup {
  kind: "group";
  key: string;         // stable identifier for open-state persistence
  label: string;
  icon: LucideIcon;
  children: NavLeaf[];
}
type NavItem = NavLeaf | NavGroup;

const leaf = (to: string, label: string, icon: LucideIcon): NavLeaf => ({
  kind: "leaf", to, label, icon,
});

// Library is grouped so its 8 sub-pages don't blow up the flat
// sidebar. All other modules stay as flat leaves for now — group
// more when they grow their own sub-pages.
// Grouped nav that matches the school-side org chart. Where a single
// existing page covers multiple sub-nav concepts (e.g. Fee Structure,
// Fee Collection and Fee Reports all live inside /fees as tabs), the
// entries share a URL — clicking any of them takes the user to the
// same page. That's intentional; splitting each tab into its own
// route is a follow-up.
const nav: NavItem[] = [
  leaf("/dashboard", "Dashboard", Home),

  // ------------------------------- School Setup
  {
    kind: "group", key: "school-setup", label: "School Setup", icon: Building,
    children: [
      leaf("/settings", "School Profile", Settings),
      leaf("/academic", "Academic Year", CalendarDays),
      leaf("/org", "Departments", Layers),
      leaf("/org", "Classes & Sections", GraduationCap),
      leaf("/curriculum", "Curriculum", BookOpenCheck),
    ],
  },

  // ------------------------------- Student Management
  {
    kind: "group", key: "students-mgmt", label: "Student Management",
    icon: GraduationCap,
    children: [
      leaf("/students", "Students", GraduationCap),
      leaf("/admissions", "Admissions", ClipboardList),
      leaf("/attendance", "Attendance", ClipboardList),
      leaf("/report-cards", "Report Cards", FileText),
      leaf("/cert-issue", "Certificates", FileText),
      leaf("/id-cards", "ID Cards", Printer),
      leaf("/discipline", "Discipline", AlertOctagon),
      leaf("/alumni", "Alumni", Users),
    ],
  },

  // ------------------------------- Staff Management
  {
    kind: "group", key: "staff-mgmt", label: "Staff Management", icon: Users,
    children: [
      leaf("/teachers", "Teachers", Users),
      leaf("/users", "Users & Logins", KeyRound),
      leaf("/staff", "Staff Attendance", CalendarCheck),
    ],
  },

  // ------------------------------- Academic Management
  {
    kind: "group", key: "academic-mgmt", label: "Academic Management",
    icon: BookOpenCheck,
    children: [
      leaf("/timetable", "Timetable", CalendarDays),
      leaf("/homework", "Homework", ClipboardList),
      leaf("/exams", "Exams", BookOpenCheck),
      leaf("/report-cards", "Report Cards", FileText),
    ],
  },

  // ------------------------------- Fee Management
  {
    kind: "group", key: "fees", label: "Fee Management", icon: Receipt,
    children: [
      leaf("/fees", "Fee Structure", Layers),
      leaf("/fees", "Fee Collection", Receipt),
      leaf("/fees", "Fee Reports", BarChart3),
    ],
  },

  // ------------------------------- Communication
  {
    kind: "group", key: "communication", label: "Communication",
    icon: MessageCircle,
    children: [
      leaf("/notice-board", "Notice Board", Bell),
      leaf("/communication", "SMS", MessageCircle),
      leaf("/communication", "Email", Send),
      leaf("/communication", "Push Notifications", Bell),
      leaf("/notice-board", "Circulars", FileText),
    ],
  },

  // ------------------------------- Library
  {
    kind: "group", key: "library", label: "Library", icon: Library,
    children: [
      leaf("/library", "Dashboard", Home),
      leaf("/library-books", "Books", BookOpen),
      leaf("/library-copies", "Book Copies", Copy),
      leaf("/library-categories", "Categories", Layers),
      leaf("/library-authors", "Authors", PenTool),
      leaf("/library-publishers", "Publishers", Building),
      leaf("/library-shelves", "Shelves & Racks", Warehouse),
      leaf("/library-issue", "Issue Books", Hand),
      leaf("/library-return", "Return Books", RotateCcw),
      leaf("/library-renew", "Renew Books", RefreshCw),
      leaf("/library-reservations", "Reservations", Clock),
      leaf("/library-fines", "Fine Management", ReceiptText),
      leaf("/library-lost", "Lost & Damaged Books", AlertOctagon),
      leaf("/library-inventory", "Inventory Verification", CheckSquare),
      leaf("/library-barcode", "Barcode Management", Printer),
      leaf("/library-reports", "Reports", BarChart3),
      leaf("/library-import-export", "Import / Export", ArrowUpDown),
      leaf("/library-notifications", "Notifications", Bell),
      leaf("/library-user-history", "User History", History),
      leaf("/library-audit", "Audit Logs", ShieldCheck),
      leaf("/library-settings", "Settings", Settings),
    ],
  },

  leaf("/transport", "Transport", Bus),
  leaf("/hostel", "Hostel", Building),

  // ------------------------------- Finance
  {
    kind: "group", key: "finance", label: "Finance", icon: Receipt,
    children: [
      leaf("/finance-expenses", "Accounts", Receipt),
      leaf("/finance-vendors", "Vendors", Users),
      leaf("/payroll-structures", "Payroll & HR", KeyRound),
      leaf("/payroll-payslips", "Payslips", FileText),
    ],
  },

  // ------------------------------- Inventory & Assets
  {
    kind: "group", key: "inventory", label: "Inventory & Assets",
    icon: Warehouse,
    children: [
      leaf("/inventory-items", "Items", BookOpen),
      leaf("/inventory-movements", "Stock Movements", ArrowUpDown),
    ],
  },

  // ------------------------------- Campus Management
  {
    kind: "group", key: "campus", label: "Campus Management", icon: Building,
    children: [
      leaf("/visitor-logs", "Visitor Management", Hand),
      leaf("/health-records", "Health / Infirmary", ShieldCheck),
      leaf("/sports-houses", "Sports Houses", PenTool),
      leaf("/sports-events", "Sports Events", CalendarDays),
    ],
  },

  leaf("/reports", "Reports", BarChart3),
  leaf("/subscription", "Subscription", CreditCard),
  leaf("/settings", "Settings", Settings),
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
 * Role-scoped sidebar. Every leaf is checked against the user's
 * ``granted_admin_pages``; a group survives if at least one of its
 * children survives. Senior leadership bypasses the filter and sees
 * the whole tree.
 *
 * The slug in ``granted_admin_pages`` matches the sidebar route path
 * with the leading slash stripped ("library-books" for "/library-books").
 */
function filterNav(
  items: NavItem[], roles: string[], granted: string[],
): NavItem[] {
  const bypass = roles.some((r) => FULL_ACCESS_ROLES.has(r));
  if (bypass) return items;
  const grantedSlugs = new Set(
    granted.map((s) => (s.startsWith("/") ? s.slice(1) : s)),
  );
  const isVisible = (l: NavLeaf) =>
    grantedSlugs.has(l.to.replace(/^\//, ""));
  const out: NavItem[] = [];
  for (const item of items) {
    if (item.kind === "leaf") {
      if (isVisible(item)) out.push(item);
    } else {
      const kids = item.children.filter(isVisible);
      if (kids.length > 0) out.push({ ...item, children: kids });
    }
  }
  return out;
}

const leafClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-saffron-pale text-saffron-darker"
      : "text-indigo/80 hover:bg-saffron-pale/60 hover:text-indigo-dark",
  );

const nestedLeafClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-md px-3 py-1.5 pl-9 text-sm transition-colors",
    isActive
      ? "bg-saffron-pale text-saffron-darker font-semibold"
      : "text-indigo/70 hover:bg-saffron-pale/40 hover:text-indigo-dark",
  );

function NavGroupSection({
  group, forceOpen,
}: {
  group: NavGroup;
  forceOpen: boolean;
}) {
  const [open, setOpen] = useState(forceOpen);
  // If the active route moves *into* the group, auto-expand.
  const effectiveOpen = open || forceOpen;
  return (
    <div className="mb-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
          forceOpen
            ? "text-saffron-darker"
            : "text-indigo/80 hover:bg-saffron-pale/60 hover:text-indigo-dark",
        )}
      >
        <group.icon className="h-4 w-4" />
        <span className="flex-1 text-left">{group.label}</span>
        {effectiveOpen ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
      </button>
      {effectiveOpen && (
        <div className="mt-1 flex flex-col gap-0.5">
          {group.children.map((c) => (
            <NavLink key={c.to} to={c.to} className={nestedLeafClass}>
              <c.icon className="h-3.5 w-3.5" />
              {c.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export function SchoolAdminLayout() {
  const user = useAuth((s) => s.user);
  const tokens = useAuth((s) => s.tokens);
  const clear = useAuth((s) => s.clear);
  const navigate = useNavigate();
  const location = useLocation();

  const visibleNav = useMemo(
    () => filterNav(nav, user?.roles ?? [], user?.granted_admin_pages ?? []),
    [user?.roles, user?.granted_admin_pages],
  );

  // Mobile drawer state. Closed by default; opens via the hamburger
  // in the top bar and auto-closes whenever the route changes so
  // navigating to a new page always leaves the reader on the page,
  // not the menu.
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const onLogout = async () => {
    try {
      await logoutApi(tokens?.refresh_token);
    } catch {
      // best-effort
    }
    clear();
    navigate("/login", { replace: true });
  };

  const currentPath = location.pathname;

  const sidebarBody = (
    <>
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
        {visibleNav.map((item) => {
          if (item.kind === "leaf") {
            return (
              <NavLink key={item.to} to={item.to} className={leafClass}>
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          }
          const forceOpen = item.children.some(
            (c) => currentPath === c.to || currentPath.startsWith(c.to + "/"),
          );
          return (
            <NavGroupSection
              key={item.key}
              group={item}
              forceOpen={forceOpen}
            />
          );
        })}
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
    </>
  );

  return (
    <div className="flex h-full flex-col bg-ivory md:grid md:grid-cols-[260px_1fr]">
      {/* Mobile top bar — hamburger + school label */}
      <header className="flex items-center gap-3 border-b border-saffron-pale bg-warm-white px-4 py-3 md:hidden">
        <button
          type="button"
          className="rounded-md p-2 text-indigo-dark hover:bg-saffron-pale/60"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-sm font-semibold text-indigo-dark">
            {user?.school_name ?? "School Admin"}
          </p>
          <p className="truncate font-mono text-[10px] uppercase tracking-widest text-saffron-dark">
            {user?.tenant_subdomain ?? "your-school"}.jaikalki.com
          </p>
        </div>
      </header>

      {/* Sidebar — permanent on md+, drawer on mobile */}
      <aside className="hidden h-full md:flex md:flex-col md:border-r md:border-saffron-pale md:bg-warm-white md:px-5 md:py-7">
        {sidebarBody}
      </aside>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85%] transform flex-col border-r border-saffron-pale bg-warm-white px-5 py-5 transition-transform md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="mb-3 flex items-center justify-end">
          <button
            type="button"
            className="rounded-md p-2 text-muted-foreground hover:bg-muted"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {sidebarBody}
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto px-4 py-4 md:px-10 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}
