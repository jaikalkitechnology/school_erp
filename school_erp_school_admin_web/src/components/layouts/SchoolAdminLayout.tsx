import { useMemo, useState } from "react";
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
const nav: NavItem[] = [
  leaf("/dashboard", "Overview", Home),
  leaf("/org", "Departments / Classes", Layers),
  leaf("/academic", "Academic year", CalendarDays),
  leaf("/curriculum", "Curriculum", BookOpenCheck),
  leaf("/students", "Students", GraduationCap),
  leaf("/teachers", "Teachers", Users),
  leaf("/staff", "Staff attendance", CalendarCheck),
  leaf("/users", "Users & logins", KeyRound),
  leaf("/attendance", "Attendance", ClipboardList),
  leaf("/timetable", "Timetable", CalendarDays),
  leaf("/homework", "Homework", ClipboardList),
  leaf("/exams", "Exams", BookOpenCheck),
  leaf("/report-cards", "Report cards", FileText),
  leaf("/fees", "Fees", Receipt),
  leaf("/communication", "Communication", MessageCircle),
  {
    kind: "group",
    key: "library",
    label: "Library",
    icon: Library,
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
  // ---- Phase 28 operational modules ----
  {
    kind: "group",
    key: "admissions",
    label: "Admissions",
    icon: GraduationCap,
    children: [
      leaf("/admissions", "Enquiry pipeline", ClipboardList),
    ],
  },
  {
    kind: "group",
    key: "finance",
    label: "Accounts / Finance",
    icon: Receipt,
    children: [
      leaf("/finance-expenses", "Expenses", Receipt),
      leaf("/finance-vendors", "Vendors", Users),
    ],
  },
  {
    kind: "group",
    key: "payroll",
    label: "Payroll / HR",
    icon: KeyRound,
    children: [
      leaf("/payroll-structures", "Salary structures", Layers),
      leaf("/payroll-payslips", "Payslips", FileText),
    ],
  },
  {
    kind: "group",
    key: "inventory",
    label: "Inventory / Stores",
    icon: Warehouse,
    children: [
      leaf("/inventory-items", "Items", BookOpen),
      leaf("/inventory-movements", "Stock movements", ArrowUpDown),
    ],
  },
  leaf("/visitor-logs", "Visitor management", Hand),
  leaf("/health-records", "Health / Infirmary", ShieldCheck),
  {
    kind: "group",
    key: "certificates",
    label: "Certificates",
    icon: FileText,
    children: [
      leaf("/cert-issue", "Issue certificate", Send),
      leaf("/cert-templates", "Templates", Layers),
    ],
  },
  leaf("/id-cards", "ID cards", Printer),
  leaf("/discipline", "Discipline", AlertOctagon),
  leaf("/notice-board", "Notice board", Bell),
  leaf("/alumni", "Alumni", Users),
  {
    kind: "group",
    key: "sports",
    label: "Sports & clubs",
    icon: PenTool,
    children: [
      leaf("/sports-houses", "Houses", Layers),
      leaf("/sports-events", "Events", CalendarDays),
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
          {visibleNav.map((item) => {
            if (item.kind === "leaf") {
              return (
                <NavLink key={item.to} to={item.to} className={leafClass}>
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            }
            // Auto-expand the group when the active route is one of its
            // children so the librarian doesn't have to click Library
            // to re-open it every time they navigate.
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
      </aside>

      <main className="overflow-y-auto px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}
