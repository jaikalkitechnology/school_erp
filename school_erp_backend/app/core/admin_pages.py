"""Catalogue of admin web pages + per-role default access maps.

The Users & credentials panel uses this to:
  * Show a checklist of pages when creating/editing a sub-admin user.
  * Pre-populate sensible defaults when the admin picks a role.

Roles that exist but aren't listed in DEFAULT_PAGES_BY_ROLE intentionally
get an empty list — meaning "mobile-app login only, no admin access".
"""

from __future__ import annotations

# (slug, human label, sidebar group). The slug matches the React route
# path under /<slug>. Keep this in sync with the React side; the admin
# UI fetches /v1/school-admin/admin-pages/_catalogue so we don't have
# to duplicate the strings on the frontend.
ADMIN_PAGES: tuple[tuple[str, str, str], ...] = (
    ("dashboard", "Dashboard", "Overview"),
    ("org", "Departments / Classes", "Setup"),
    ("academic", "Academic year", "Setup"),
    ("curriculum", "Curriculum", "Setup"),
    ("students", "Students", "SIS"),
    ("teachers", "Teachers", "SIS"),
    ("staff", "Staff attendance", "SIS"),
    ("users", "Users & logins", "SIS"),
    ("attendance", "Attendance", "Academics"),
    ("timetable", "Timetable", "Academics"),
    ("homework", "Homework", "Academics"),
    ("exams", "Exams", "Academics"),
    ("report-cards", "Report cards", "Academics"),
    ("fees", "Fees", "Finance"),
    ("communication", "Communication", "Comms"),
    # Library is split into 7 sub-pages so the school admin can grant
    # (say) Issue + Return access without also handing over the whole
    # catalogue. Slugs match the React route paths.
    ("library", "Library dashboard", "Library"),
    ("library-books", "Books", "Library"),
    ("library-copies", "Book copies", "Library"),
    ("library-categories", "Categories", "Library"),
    ("library-authors", "Authors", "Library"),
    ("library-publishers", "Publishers", "Library"),
    ("library-shelves", "Shelves & racks", "Library"),
    ("library-issue", "Issue books", "Library"),
    ("library-return", "Return books", "Library"),
    ("library-renew", "Renew books", "Library"),
    ("library-reservations", "Reservations", "Library"),
    ("library-fines", "Fine management", "Library"),
    ("library-lost", "Lost & damaged books", "Library"),
    ("library-inventory", "Inventory verification", "Library"),
    ("library-barcode", "Barcode management", "Library"),
    ("library-reports", "Library reports", "Library"),
    ("library-import-export", "Import / export", "Library"),
    ("library-notifications", "Library notifications", "Library"),
    ("library-user-history", "User history", "Library"),
    ("library-audit", "Library audit logs", "Library"),
    ("library-settings", "Library settings", "Library"),
    # ---- Phase 28 operational modules ----
    ("admissions", "Admissions pipeline", "Admissions"),
    ("finance-expenses", "Expenses", "Accounts / Finance"),
    ("finance-vendors", "Vendors", "Accounts / Finance"),
    ("payroll-structures", "Salary structures", "Payroll / HR"),
    ("payroll-payslips", "Payslips", "Payroll / HR"),
    ("inventory-items", "Inventory items", "Inventory / Stores"),
    ("inventory-movements", "Stock movements", "Inventory / Stores"),
    ("visitor-logs", "Visitor management", "Front desk"),
    ("health-records", "Health / Infirmary", "Wellbeing"),
    ("cert-issue", "Issue certificate", "Certificates"),
    ("cert-templates", "Certificate templates", "Certificates"),
    ("id-cards", "ID cards", "Certificates"),
    ("discipline", "Discipline register", "Wellbeing"),
    ("notice-board", "Notice board", "Comms"),
    ("alumni", "Alumni directory", "Community"),
    ("sports-houses", "Sports houses", "Sports & clubs"),
    ("sports-events", "Sports events", "Sports & clubs"),
    ("transport", "Transport", "Operations"),
    ("hostel", "Hostel", "Operations"),
    ("reports", "Reports", "Insights"),
    ("subscription", "Subscription", "Account"),
    ("settings", "Settings", "Account"),
)

PAGE_SLUGS: frozenset[str] = frozenset(p[0] for p in ADMIN_PAGES)

# Every page slug — the "full admin" preset.
ALL_PAGES: tuple[str, ...] = tuple(p[0] for p in ADMIN_PAGES)

# Role → default page set when a new user with this role is created
# via the Users & credentials panel. The admin can still uncheck or
# add pages individually in the dialog; this is just the starting
# point.
DEFAULT_PAGES_BY_ROLE: dict[str, tuple[str, ...]] = {
    # --- Full admin web access ---------------------------------------
    "vice_principal": ALL_PAGES,
    "coordinator": ALL_PAGES,
    "accountant": (
        "dashboard", "students", "fees", "communication", "reports",
        "subscription", "finance-expenses", "finance-vendors",
    ),
    # Phase 28 org-chart specialists.
    "accounts": (
        "dashboard", "students", "fees", "reports",
        "finance-expenses", "finance-vendors",
    ),
    "payroll": (
        "dashboard", "teachers", "reports",
        "payroll-structures", "payroll-payslips",
    ),
    "office_admin": (
        "dashboard", "students", "teachers", "admissions",
        "visitor-logs", "notice-board", "id-cards",
        "cert-issue", "cert-templates",
    ),
    "office_staff": (
        "dashboard", "students", "admissions", "visitor-logs",
        "notice-board", "cert-issue", "id-cards",
    ),
    "receptionist": (
        "dashboard", "visitor-logs", "notice-board", "admissions",
    ),
    "data_entry_operator": (
        "dashboard", "students", "teachers", "attendance",
        "admissions", "alumni",
    ),

    # --- Visible-but-narrow surfaces ---------------------------------
    "supervisor": (
        "dashboard", "students", "teachers", "attendance",
        "communication", "reports",
    ),
    "visitor_desk": ("dashboard", "students", "communication", "visitor-logs"),

    # --- Visible-but-narrow surfaces (contd.) ------------------------
    # Librarian runs only the library module. Their sidebar is
    # scoped to the seven Library sub-pages — no Overview, no other
    # modules — so the login surface stays focused on their job.
    # The school admin can still uncheck individual boxes (eg. hide
    # Fine management from a junior librarian) on Users & credentials.
    "librarian": (
        "library",
        "library-books",
        "library-copies",
        "library-categories",
        "library-authors",
        "library-publishers",
        "library-shelves",
        "library-issue",
        "library-return",
        "library-renew",
        "library-reservations",
        "library-fines",
        "library-lost",
        "library-inventory",
        "library-barcode",
        "library-reports",
        "library-import-export",
        "library-notifications",
        "library-user-history",
        "library-audit",
        "library-settings",
    ),

    # --- Mobile-app-only (no admin web sidebar at all) ----------------
    "class_teacher": (),
    "subject_teacher": (),
    "transport_manager": (),
    "hostel_warden": (),
    "bus_staff": (),
    "parent": (),
    "student": (),
}


def default_pages_for_roles(role_codes: list[str]) -> list[str]:
    """Union the default page sets for the given roles. Used when the
    admin picks one or more roles and we need a starting checklist."""
    out: set[str] = set()
    for code in role_codes:
        for slug in DEFAULT_PAGES_BY_ROLE.get(code, ()):
            out.add(slug)
    return [s for s in ALL_PAGES if s in out]


def sanitize_pages(pages: list[str]) -> list[str]:
    """Drop any slugs the admin sent that aren't real pages — typos,
    rename leftovers, etc. — and preserve catalogue order so the JSON
    column stays stable across saves."""
    asked = set(pages or [])
    return [s for s in ALL_PAGES if s in asked]
