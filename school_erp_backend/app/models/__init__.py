"""SQLAlchemy ORM models. Importing this package registers every table."""

from app.models.academic import (  # noqa: F401
    AcademicTerm,
    AcademicYear,
    ClassDef,
    ClassStage,
    ClassSubject,
    Department,
    Holiday,
    HolidayKind,
    Section,
    Subject,
)
from app.models.audit import AuditLog  # noqa: F401
from app.models.curriculum import (  # noqa: F401
    CalendarEvent,
    CalendarEventKind,
    Chapter,
    House,
    SectionSubject,
    Syllabus,
)
from app.models.auth import (  # noqa: F401
    AuthProvider,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.models.parent import (  # noqa: F401
    Parent,
    ParentChildMapping,
    ParentSession,
    Relation,
    Student,
)
from app.models.tenant import (  # noqa: F401
    BillingCycle,
    SchoolType,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    TenantSettings,
    TenantStatus,
    TenantUsageSnapshot,
)
