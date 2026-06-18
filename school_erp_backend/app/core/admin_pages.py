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
    ("library", "Library", "Operations"),
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
        "subscription",
    ),

    # --- Visible-but-narrow surfaces ---------------------------------
    "supervisor": (
        "dashboard", "students", "teachers", "attendance",
        "communication", "reports",
    ),
    "visitor_desk": ("dashboard", "students", "communication"),

    # --- Mobile-app-only (no admin web sidebar at all) ----------------
    "class_teacher": (),
    "subject_teacher": (),
    "librarian": (),
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
