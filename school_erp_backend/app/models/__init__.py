"""SQLAlchemy ORM models. Importing this package registers every table."""

from app.models.audit import AuditLog  # noqa: F401
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
