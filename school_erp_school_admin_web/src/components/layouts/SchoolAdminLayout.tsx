import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
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
  Search,
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
import { useQuery } from "@tanstack/react-query";
import { JaikalkiIcon, SchoolLogo, useSchoolFavicon } from "@/components/SchoolLogo";
import { fetchBranding } from "@/lib/branding-api";
import { NotificationBell } from "./NotificationBell";

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
      leaf("/fees?tab=Categories", "Fee Categories", Layers),
      leaf("/fees?tab=Structures", "Fee Structure", Layers),
      leaf("/fees?tab=Collection", "Fee Collection", Receipt),
      leaf("/fees?tab=Reports", "Fee Reports", BarChart3),
    ],
  },

  // ------------------------------- Communication
  {
    kind: "group", key: "communication", label: "Communication",
    icon: MessageCircle,
    children: [
      leaf("/notice-board", "Notice Board", Bell),
      leaf("/communication?tab=Announcements", "Announcements", Bell),
      leaf("/communication?tab=Messages", "Messages", MessageCircle),
      leaf("/communication?tab=Templates", "Templates", FileText),
      leaf("/communication?tab=Outbox", "Outbox (SMS/Email/Push)", Send),
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
  // Match on the pathname only — a leaf's `to` may carry a ?tab= deep-link.
  const isVisible = (l: NavLeaf) =>
    grantedSlugs.has(l.to.split("?")[0].replace(/^\//, ""));
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

// ---- Sidebar search ------------------------------------------------------
// Extra words people type for a page whose label doesn't contain them
// (eg. "bus" → Transport). Keyed by route path without the ?tab= part.
const KEYWORDS: Record<string, string> = {
  "/dashboard": "home overview",
  "/settings": "school profile logo address",
  "/org": "class section department",
  "/students": "pupil child admit enrol",
  "/attendance": "absent present roll call",
  "/teachers": "staff faculty",
  "/users": "login password credentials account role access",
  "/staff": "teacher attendance",
  "/exams": "marks test grade result",
  "/report-cards": "marks result grade",
  "/fees": "payment invoice due receipt",
  "/communication": "sms email push message whatsapp",
  "/notice-board": "circular announcement",
  "/transport": "bus driver route stop vehicle fleet gps",
  "/hostel": "room warden dorm boarding",
  "/finance-expenses": "expense money accounts",
  "/payroll-structures": "salary pay",
  "/payroll-payslips": "salary pay",
  "/inventory-items": "stock store assets",
  "/visitor-logs": "gate visitor entry",
  "/health-records": "medical doctor sick nurse",
};

function leafMatches(l: NavLeaf, terms: string[]): boolean {
  const path = l.to.split("?")[0];
  const libraryWords = path.startsWith("/library") ? " book library" : "";
  const hay = `${l.label} ${KEYWORDS[path] ?? ""}${libraryWords}`.toLowerCase();
  return terms.every((t) => hay.includes(t));
}

/** Narrow the (already role-filtered) nav to items matching the query.
 *  A group whose own name matches keeps all its pages; otherwise it keeps
 *  only the matching pages, and disappears if none match. */
function searchNav(items: NavItem[], query: string): NavItem[] {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return items;
  const out: NavItem[] = [];
  for (const item of items) {
    if (item.kind === "leaf") {
      if (leafMatches(item, terms)) out.push(item);
      continue;
    }
    const groupHit = terms.every((t) => item.label.toLowerCase().includes(t));
    const kids = groupHit ? item.children : item.children.filter((c) => leafMatches(c, terms));
    if (kids.length > 0) out.push({ ...item, children: kids });
  }
  return out;
}

function firstLeaf(items: NavItem[]): NavLeaf | null {
  for (const item of items) {
    if (item.kind === "leaf") return item;
    if (item.children.length > 0) return item.children[0];
  }
  return null;
}

/** Marks the typed text inside a menu label. Always one <span>, so the
 *  label stays a single flex item inside the nav link. */
function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim().toLowerCase();
  const i = q ? text.toLowerCase().indexOf(q) : -1;
  if (i < 0) return <span>{text}</span>;
  return (
    <span>
      {text.slice(0, i)}
      <mark className="rounded bg-marigold-pale px-0.5 text-inherit">{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </span>
  );
}

/** Where the user is, for the top bar: "Fee Management › Fee Collection".
 *  Exact path (and ?tab=) wins; otherwise the deepest nav path that
 *  prefixes the URL (eg. /students/42 → Students). */
function findCrumb(
  items: NavItem[], pathname: string, search: string,
): { group?: string; label: string } | null {
  const tab = new URLSearchParams(search).get("tab");
  let exact: { group?: string; label: string } | null = null;
  let prefix: { group?: string; label: string; len: number } | null = null;
  for (const item of items) {
    const group = item.kind === "group" ? item.label : undefined;
    const leaves = item.kind === "leaf" ? [item] : item.children;
    for (const l of leaves) {
      const [path, qs] = l.to.split("?");
      if (path === pathname) {
        const leafTab = qs ? new URLSearchParams(qs).get("tab") : null;
        if (leafTab && leafTab === tab) return { group, label: l.label };
        if (!exact) exact = { group, label: l.label };
      } else if (pathname.startsWith(path + "/") && (!prefix || path.length > prefix.len)) {
        prefix = { group, label: l.label, len: path.length };
      }
    }
  }
  return exact ?? (prefix && { group: prefix.group, label: prefix.label });
}

const SIDEBAR_KEY = "jaikalki.sidebar.collapsed";

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

/** Active state for a leaf whose link carries a query (eg. the Communication
 *  tabs, which all share /communication). NavLink only compares the path,
 *  so it would light up every tab at once. With no tab in the URL the page
 *  shows its first tab, so the first such link counts as active. */
function queryLeafActive(to: string, loc: { pathname: string; search: string }, siblings: string[]): boolean {
  const [path, qs = ""] = to.split("?");
  if (loc.pathname !== path) return false;
  const have = new URLSearchParams(loc.search);
  for (const [k, v] of new URLSearchParams(qs)) {
    const cur = have.get(k);
    if (cur === null) return siblings.find((x) => x.split("?")[0] === path) === to;
    if (cur !== v) return false;
  }
  return true;
}

function NavGroupSection({
  group, forceOpen, query = "", initiallyOpen = false,
}: {
  group: NavGroup;
  forceOpen: boolean;
  query?: string;
  /** Start expanded (eg. its icon was clicked in the collapsed rail). */
  initiallyOpen?: boolean;
}) {
  const [open, setOpen] = useState(forceOpen || initiallyOpen);
  const location = useLocation();
  const siblings = group.children.map((c) => c.to);
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
        <span className="flex-1 text-left"><Highlight text={group.label} query={query} /></span>
        {effectiveOpen ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
      </button>
      {effectiveOpen && (
        <div className="mt-1 flex flex-col gap-0.5">
          {group.children.map((c) => (
            <NavLink
              key={`${c.to}|${c.label}`}
              to={c.to}
              className={({ isActive }) =>
                nestedLeafClass({ isActive: c.to.includes("?") ? queryLeafActive(c.to, location, siblings) : isActive })
              }
            >
              <c.icon className="h-3.5 w-3.5" />
              <Highlight text={c.label} query={query} />
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
  const [query, setQuery] = useState("");
  // Leaving the page (or switching ?tab=) closes the drawer and resets
  // the search so the full menu is back next time.
  useEffect(() => {
    setMobileOpen(false);
    setQuery("");
  }, [location.pathname, location.search]);

  // Desktop: the top-bar hamburger hides/shows the sidebar. Remembered
  // per browser; storage can be unavailable (private mode), so guard it.
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

  // Section to open when the full menu is expanded from its rail icon.
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const isPhone = () => window.matchMedia("(max-width: 767px)").matches;
  const onMenuButton = () => {
    if (isPhone()) {
      setMobileOpen(true);
      return;
    }
    setOpenGroup(null);
    setCollapsed((c) => !c);
  };
  const expandTo = (groupKey: string | null) => {
    setOpenGroup(groupKey);
    setCollapsed(false);
  };

  const searching = query.trim().length > 0;
  const shownNav = useMemo(() => searchNav(visibleNav, query), [visibleNav, query]);

  const onSearchKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const hit = firstLeaf(shownNav);
      if (hit) {
        e.preventDefault();
        navigate(hit.to);
      }
    } else if (e.key === "Escape") {
      setQuery("");
      e.currentTarget.blur();
    }
  };

  // "/" or Ctrl/Cmd+K jumps to the sidebar search from anywhere, unless
  // the user is already typing in a field.
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = !!el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
      const shortcut = (e.key === "k" && (e.ctrlKey || e.metaKey)) || (e.key === "/" && !typing);
      if (!shortcut) return;
      e.preventDefault();
      if (isPhone()) setMobileOpen(true);
      else if (collapsed) setCollapsed(false);
      // Focus after React re-renders, so a just-reopened sidebar is no
      // longer inert.
      window.setTimeout(() => {
        const input = Array.from(
          document.querySelectorAll<HTMLInputElement>("[data-sidebar-search]"),
        ).find((i) => i.offsetParent !== null && !i.closest("[inert]"));
        input?.focus();
        input?.select();
      }, 0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [collapsed]);

  const onLogout = async () => {
    try {
      await logoutApi(tokens?.refresh_token);
    } catch {
      // best-effort
    }
    clear();
    navigate("/login", { replace: true });
  };

  // Logo + current school name (School Profile changes show up without
  // signing out again).
  const branding = useQuery({
    queryKey: ["branding"],
    queryFn: fetchBranding,
    staleTime: 5 * 60_000,
  });
  const schoolName = branding.data?.school_name ?? user?.school_name ?? "School Admin";
  useSchoolFavicon(branding.data?.logo_url);

  const currentPath = location.pathname;
  const crumb = useMemo(
    () => findCrumb(nav, location.pathname, location.search),
    [location.pathname, location.search],
  );

  const sidebarBody = (
    <>
      <div className="mb-6 flex items-center gap-3">
        <SchoolLogo
          src={branding.data?.logo_url}
          alt={`${schoolName} logo`}
          className="h-12 w-12 shrink-0 rounded-lg border border-saffron-pale bg-white object-contain p-1"
          fallback={<JaikalkiIcon className="h-12 w-12 shrink-0 rounded-xl shadow" />}
        />
        <div className="min-w-0">
          <p className="font-display text-lg font-semibold leading-tight text-indigo-dark">
            {schoolName}
          </p>
        </div>
      </div>

      {visibleNav.length > 0 && (
        <div className="relative mb-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            data-sidebar-search
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onSearchKey}
            placeholder="Search menu…"
            aria-label="Search menu"
            autoComplete="off"
            spellCheck={false}
            className="h-9 w-full rounded-md border border-saffron-pale bg-ivory pl-9 pr-9 text-sm text-indigo-dark placeholder:text-muted-foreground focus:border-saffron focus:outline-none focus:ring-2 focus:ring-saffron/30"
          />
          {searching ? (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-saffron-pale/60 hover:text-indigo-dark"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : (
            <kbd className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded border border-saffron-pale px-1.5 font-mono text-[10px] text-muted-foreground md:block">
              /
            </kbd>
          )}
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
        {visibleNav.length === 0 && (
          <p className="rounded-md bg-marigold-pale/40 px-3 py-2 text-xs text-marigold-dark">
            You don't have any admin pages assigned yet. Please use the
            mobile app, or ask your school admin to grant page access.
          </p>
        )}
        {searching && shownNav.length === 0 && (
          <p className="px-3 py-2 text-sm text-muted-foreground">
            No pages match “{query.trim()}”.
          </p>
        )}
        {shownNav.map((item) => {
          if (item.kind === "leaf") {
            return (
              <NavLink key={`${item.to}|${item.label}`} to={item.to} className={leafClass}>
                <item.icon className="h-4 w-4" />
                <Highlight text={item.label} query={query} />
              </NavLink>
            );
          }
          const forceOpen = searching || item.children.some((c) => {
            const path = c.to.split("?")[0];
            return currentPath === path || currentPath.startsWith(path + "/");
          });
          return (
            <NavGroupSection
              key={item.key}
              group={item}
              forceOpen={forceOpen}
              query={query}
              initiallyOpen={item.key === openGroup}
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

  // Collapsed desktop sidebar: logo + school name, then one icon per
  // top-level item. Page icons navigate; section icons open the full menu
  // with that section expanded.
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
        onClick={() => expandTo(null)}
        title="Open menu"
        className="mb-5 flex flex-col items-center gap-2 rounded-lg px-1 py-1 hover:bg-saffron-pale/40"
      >
        <SchoolLogo
          src={branding.data?.logo_url}
          alt={`${schoolName} logo`}
          className="h-11 w-11 rounded-xl border border-saffron-pale bg-white object-contain p-1"
          fallback={<JaikalkiIcon className="h-11 w-11 rounded-xl shadow" />}
        />
        <span className="line-clamp-3 text-center font-display text-[11px] font-semibold leading-tight text-indigo-dark">
          {schoolName}
        </span>
      </button>

      <nav aria-label="Main" className="flex flex-1 flex-col items-center gap-2 overflow-y-auto [scrollbar-width:none]">
        {visibleNav.map((item) => {
          if (item.kind === "leaf") {
            return (
              <NavLink
                key={`${item.to}|${item.label}`}
                to={item.to}
                title={item.label}
                aria-label={item.label}
                className={({ isActive }) => railItem(isActive)}
              >
                <item.icon className="h-5 w-5" />
              </NavLink>
            );
          }
          const inside = item.children.some((c) => {
            const path = c.to.split("?")[0];
            return currentPath === path || currentPath.startsWith(path + "/");
          });
          return (
            <button
              key={item.key}
              type="button"
              title={item.label}
              aria-label={`${item.label} — open menu`}
              onClick={() => expandTo(item.key)}
              className={railItem(inside)}
            >
              <item.icon className="h-5 w-5" />
            </button>
          );
        })}
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
    <div className="flex h-full flex-col bg-ivory md:flex-row print:block print:h-auto print:bg-white">
      {/* Sidebar on md+: full menu, or (☰) a slim icon rail. On mobile the
          drawer below. Inner width is fixed so content doesn't reflow
          while the width animates. */}
      <aside
        id="admin-sidebar"
        className={cn(
          "hidden h-full shrink-0 overflow-hidden border-r border-saffron-pale bg-warm-white transition-[width] duration-200 ease-out motion-reduce:transition-none md:block print:!hidden",
          collapsed ? "md:w-[96px]" : "md:w-[260px]",
        )}
      >
        {collapsed ? (
          <div className="flex h-full w-[96px] flex-col items-center px-2 py-6">{railBody}</div>
        ) : (
          <div className="flex h-full w-[260px] flex-col px-5 py-7">{sidebarBody}</div>
        )}
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
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85%] transform flex-col border-r border-saffron-pale bg-warm-white px-5 py-5 transition-transform md:hidden print:hidden",
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

      {/* Content column: the top bar sits outside the scrolling <main>,
          so it stays pinned while the page scrolls. */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col print:block">
        <header className="z-30 flex h-14 shrink-0 items-center gap-3 border-b border-saffron-pale bg-warm-white px-3 md:px-6 print:hidden">
          {/* Phone: opens the drawer. Desktop: hides / shows the sidebar. */}
          <button
            type="button"
            className="rounded-md p-2 text-indigo-dark hover:bg-saffron-pale/60"
            onClick={onMenuButton}
            aria-label="Toggle menu"
            aria-controls="admin-sidebar"
            title={collapsed ? "Show menu" : "Hide menu"}
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Phone: page + school. Desktop: breadcrumb. */}
          <div className="min-w-0 flex-1 md:hidden">
            <p className="truncate font-display text-sm font-semibold text-indigo-dark">
              {crumb?.label ?? schoolName}
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              {schoolName}
            </p>
          </div>
          <nav aria-label="Breadcrumb" className="hidden min-w-0 flex-1 items-center gap-1.5 text-sm md:flex">
            {crumb?.group && (
              <>
                <span className="truncate text-muted-foreground">{crumb.group}</span>
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              </>
            )}
            <span className="truncate font-semibold text-indigo-dark">
              {crumb?.label ?? schoolName}
            </span>
          </nav>

          <NotificationBell />
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto px-4 py-4 md:px-10 md:py-8 print:overflow-visible print:p-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
