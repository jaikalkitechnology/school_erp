"""System role + permission catalogue.

Single source of truth used by the seed step. Tweaking a role's grants here
and re-running the seed updates every tenant's permission set.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleSpec:
    code: str
    name: str
    level: int
    description: str
    grants: tuple[str, ...]  # supports "*" wildcards on the prefix


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    name: str
    category: str
    description: str = ""


PERMISSIONS: tuple[PermissionSpec, ...] = (
    # Platform / tenant
    PermissionSpec("tenant.read", "View tenant settings", "tenant"),
    PermissionSpec("tenant.update", "Update tenant settings", "tenant"),
    PermissionSpec("tenant.billing", "Manage billing", "tenant"),
    PermissionSpec("tenant.audit", "View audit log", "tenant"),
    PermissionSpec("platform.tenants.manage", "Manage all tenants (super admin)", "platform"),
    PermissionSpec("platform.plans.manage", "Manage subscription plans", "platform"),
    PermissionSpec("platform.impersonate", "Impersonate any tenant", "platform"),

    # Users + roles
    PermissionSpec("user.read", "View users", "user"),
    PermissionSpec("user.create", "Create users", "user"),
    PermissionSpec("user.update", "Update users", "user"),
    PermissionSpec("user.delete", "Deactivate users", "user"),
    PermissionSpec("user.role.assign", "Assign roles", "user"),
    PermissionSpec("user.password.reset", "Reset user passwords", "user"),

    # SIS - student
    PermissionSpec("student.view.self", "View own student profile", "student"),
    PermissionSpec("student.view.class", "View students in class", "student"),
    PermissionSpec("student.view.all", "View all students", "student"),
    PermissionSpec("student.create", "Admit student", "student"),
    PermissionSpec("student.update", "Edit student profile", "student"),
    PermissionSpec("student.delete", "Deactivate student", "student"),
    PermissionSpec("student.documents.upload", "Upload student documents", "student"),

    # Teacher
    PermissionSpec("teacher.view.self", "View own profile", "teacher"),
    PermissionSpec("teacher.view.all", "View all teachers", "teacher"),
    PermissionSpec("teacher.create", "Create teacher", "teacher"),
    PermissionSpec("teacher.update", "Update teacher", "teacher"),
    PermissionSpec("teacher.delete", "Deactivate teacher", "teacher"),

    # Parent
    PermissionSpec("parent.view.self", "View own parent profile", "parent"),
    PermissionSpec("parent.view.all", "View all parents", "parent"),
    PermissionSpec("parent.children.switch", "Switch active child", "parent"),

    # Attendance
    PermissionSpec("attendance.view.self", "View own attendance", "attendance"),
    PermissionSpec("attendance.view.class", "View class attendance", "attendance"),
    PermissionSpec("attendance.view.all", "View school-wide attendance", "attendance"),
    PermissionSpec("attendance.mark", "Mark attendance", "attendance"),
    PermissionSpec("attendance.update", "Update attendance", "attendance"),

    # Exams
    PermissionSpec("exam.view.self", "View own exam results", "exam"),
    PermissionSpec("exam.view.class", "View class exam results", "exam"),
    PermissionSpec("exam.view.all", "View all exam results", "exam"),
    PermissionSpec("exam.create", "Create exam", "exam"),
    PermissionSpec("exam.publish", "Publish results", "exam"),
    PermissionSpec("exam.grade", "Enter marks", "exam"),

    # Fees
    PermissionSpec("fee.view.self", "View own fee status", "fee"),
    PermissionSpec("fee.view.all", "View all fee accounts", "fee"),
    PermissionSpec("fee.collect", "Collect fee", "fee"),
    PermissionSpec("fee.refund", "Issue refund", "fee"),
    PermissionSpec("fee.structure.manage", "Manage fee structure", "fee"),

    # Communication
    PermissionSpec("communication.send.class", "Send to a class", "communication"),
    PermissionSpec("communication.send.all", "Send school-wide announcements", "communication"),
    PermissionSpec("communication.read", "Read announcements", "communication"),

    # Timetable
    PermissionSpec("timetable.view.self", "View own timetable", "timetable"),
    PermissionSpec("timetable.view.all", "View all timetables", "timetable"),
    PermissionSpec("timetable.manage", "Manage timetable + substitutions", "timetable"),

    # Homework
    PermissionSpec("homework.view.self", "View own homework", "homework"),
    PermissionSpec("homework.view.class", "View class homework", "homework"),
    PermissionSpec("homework.create", "Assign homework", "homework"),
    PermissionSpec("homework.grade", "Grade submissions", "homework"),

    # Library
    PermissionSpec("library.view", "View library", "library"),
    PermissionSpec("library.manage", "Manage library", "library"),
    PermissionSpec("library.checkout", "Issue + return books", "library"),

    # Transport
    PermissionSpec("transport.view.self", "View own bus", "transport"),
    PermissionSpec("transport.view.all", "View all routes", "transport"),
    PermissionSpec("transport.manage", "Manage routes + drivers", "transport"),

    # Hostel
    PermissionSpec("hostel.view", "View hostel rosters", "hostel"),
    PermissionSpec("hostel.manage", "Manage hostel", "hostel"),

    # Reports
    PermissionSpec("reports.view", "View reports", "reports"),
    PermissionSpec("reports.export", "Export reports", "reports"),
)


# Each role's grants. "tenant.*" means every permission whose code starts with "tenant.".
ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        code="super_admin",
        name="Super Admin",
        level=10,
        description="Jaikalki platform owner. Manages every school.",
        grants=("platform.*", "tenant.*", "user.*", "reports.*"),
    ),
    RoleSpec(
        code="school_admin",
        name="School Admin",
        level=9,
        description="Per-school administrator. Full school control.",
        grants=(
            "tenant.read", "tenant.update", "tenant.audit",
            "user.*", "student.*", "teacher.*", "parent.*",
            "attendance.*", "exam.*", "fee.*", "communication.*",
            "timetable.*", "homework.*", "library.*", "transport.*",
            "hostel.*", "reports.*",
        ),
    ),
    RoleSpec(
        code="principal",
        name="Principal",
        level=8,
        description="Educational head with school-wide read + approval rights.",
        grants=(
            "tenant.read", "tenant.audit",
            "user.read", "student.view.all", "teacher.view.all", "parent.view.all",
            "attendance.view.all", "exam.*", "fee.view.all",
            "communication.send.all", "communication.read",
            "timetable.*", "homework.view.class", "library.view",
            "transport.view.all", "hostel.view", "reports.*",
        ),
    ),
    RoleSpec(
        code="vice_principal",
        name="Vice Principal",
        level=7,
        description="Deputy to the principal.",
        grants=(
            "tenant.read",
            "student.view.all", "teacher.view.all", "parent.view.all",
            "attendance.view.all", "exam.view.all", "fee.view.all",
            "communication.send.class", "communication.send.all", "communication.read",
            "timetable.view.all", "library.view", "transport.view.all",
            "reports.view",
        ),
    ),
    RoleSpec(
        code="coordinator",
        name="Head Teacher / Coordinator",
        level=6,
        description="Department head. Supervises a band of classes.",
        grants=(
            "student.view.class", "teacher.view.all",
            "attendance.view.class", "attendance.update",
            "exam.view.class", "exam.grade",
            "communication.send.class", "communication.read",
            "timetable.view.all", "homework.view.class",
        ),
    ),
    RoleSpec(
        code="class_teacher",
        name="Class Teacher",
        level=5,
        description="Mentor for a single class.",
        grants=(
            "student.view.class", "parent.view.all",
            "attendance.view.class", "attendance.mark", "attendance.update",
            "exam.view.class", "exam.grade",
            "communication.send.class", "communication.read",
            "timetable.view.self", "homework.view.class", "homework.create", "homework.grade",
        ),
    ),
    RoleSpec(
        code="subject_teacher",
        name="Subject Teacher",
        level=5,
        description="Subject specialist across multiple classes.",
        grants=(
            "student.view.class",
            "attendance.view.class", "attendance.mark",
            "exam.view.class", "exam.grade",
            "communication.send.class", "communication.read",
            "timetable.view.self", "homework.view.class", "homework.create", "homework.grade",
        ),
    ),
    RoleSpec(
        code="accountant",
        name="Accountant",
        level=4,
        description="Owns fee collection.",
        grants=(
            "user.read", "student.view.all", "parent.view.all",
            "fee.*", "communication.send.class", "communication.read",
            "reports.view", "reports.export",
        ),
    ),
    RoleSpec(
        code="librarian",
        name="Librarian",
        level=4,
        description="Library operations.",
        grants=(
            "user.read", "student.view.all",
            "library.*", "reports.view",
        ),
    ),
    RoleSpec(
        code="transport_manager",
        name="Transport Manager",
        level=4,
        description="Manages buses, routes, drivers.",
        grants=(
            "user.read", "student.view.all", "parent.view.all",
            "transport.*", "communication.send.class", "communication.read",
            "reports.view",
        ),
    ),
    RoleSpec(
        code="bus_staff",
        name="Bus Staff",
        level=3,
        description="Bus driver / conductor — marks pickup-drop attendance.",
        grants=(
            "user.read", "student.view.all", "parent.view.all",
            "transport.view", "transport.attendance.mark",
            "communication.read",
        ),
    ),
    RoleSpec(
        code="supervisor",
        name="Area Supervisor",
        level=4,
        description=(
            "Multi-section / area supervisor. Read-only view across "
            "students, attendance, fees for the zone they cover."
        ),
        grants=(
            "user.read", "student.view.all", "parent.view.all",
            "teacher.view.all", "attendance.view.all", "exam.view.all",
            "fee.view", "communication.send.class", "communication.read",
            "reports.view",
        ),
    ),
    RoleSpec(
        code="visitor_desk",
        name="Visitor Desk",
        level=2,
        description="Front-desk operator for visitor check-in / out.",
        grants=(
            "user.read", "visitor.*", "communication.read",
        ),
    ),
    RoleSpec(
        code="hostel_warden",
        name="Hostel Warden",
        level=4,
        description="Hostel operations.",
        grants=(
            "user.read", "student.view.all", "parent.view.all",
            "hostel.*", "communication.send.class", "communication.read",
            "reports.view",
        ),
    ),
    RoleSpec(
        code="office_staff",
        name="Office Staff",
        level=3,
        description="Front desk, admissions support.",
        grants=(
            "user.read", "student.view.all", "parent.view.all", "teacher.view.all",
            "communication.read", "reports.view",
        ),
    ),
    RoleSpec(
        code="parent",
        name="Parent",
        level=2,
        description="Parent / guardian. Multi-child support via child switcher.",
        grants=(
            "parent.view.self", "parent.children.switch",
            "student.view.self", "attendance.view.self",
            "exam.view.self", "fee.view.self", "fee.collect",
            "communication.read", "homework.view.self",
            "timetable.view.self", "transport.view.self",
        ),
    ),
    RoleSpec(
        code="student",
        name="Student",
        level=1,
        description="Student (used for senior classes).",
        grants=(
            "student.view.self", "attendance.view.self",
            "exam.view.self", "homework.view.self",
            "timetable.view.self", "communication.read",
            "library.view",
        ),
    ),
)


def expand_grants(grants: tuple[str, ...]) -> set[str]:
    """Expand wildcard grants like ``tenant.*`` into the literal codes from ``PERMISSIONS``."""
    expanded: set[str] = set()
    for g in grants:
        if g.endswith("*"):
            prefix = g[:-1]  # keep the trailing dot
            for p in PERMISSIONS:
                if p.code.startswith(prefix):
                    expanded.add(p.code)
        else:
            expanded.add(g)
    return expanded
