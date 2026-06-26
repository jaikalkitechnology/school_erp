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
from app.models.attendance import StudentAttendance, StudentAttendanceStatus  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.billing import (  # noqa: F401
    BillingInvoice,
    BillingInvoiceStatus,
    BillingPayment,
    BillingPaymentMethod,
    BillingPaymentStatus,
    BillingRefund,
)
from app.models.comms import (  # noqa: F401
    Announcement,
    AnnouncementAudience,
    Channel,
    DeliveryStatus,
    Message,
    Notification,
    NotificationOutbox,
    NotificationTemplate,
)
from app.models.fees import (  # noqa: F401
    DiscountKind,
    FeeCategory,
    FeeDiscount,
    FeeInvoice,
    FeeInvoiceStatus,
    FeePayment,
    FeePeriod,
    FeeStructure,
    PaymentMethod,
    PaymentStatus,
)
from app.models.homework import (  # noqa: F401
    Homework,
    HomeworkSubmission,
    SubmissionStatus,
)
from app.models.hostel import (  # noqa: F401
    DisciplinaryRecord,
    DisciplinarySeverity,
    Hostel,
    HostelAllocation,
    HostelKind,
    HostelLeave,
    HostelLeaveStatus,
    MealType,
    MessMenu,
    Room,
    RoomStatus,
    VisitorLog,
)
from app.models.library import (  # noqa: F401
    Book,
    BookCopy,
    BorrowerKind,
    CopyStatus,
    Loan,
    LoanStatus,
    Reservation,
    ReservationStatus,
)
from app.models.curriculum import (  # noqa: F401
    CalendarEvent,
    CalendarEventKind,
    Chapter,
    House,
    SectionSubject,
    Syllabus,
)
from app.models.exams import (  # noqa: F401
    Exam,
    ExamMarks,
    ExamStatus,
    ExamSubject,
    ExamType,
    GradeScale,
    MarkStatus,
)
from app.models.report_cards import (  # noqa: F401
    CoCurricularGrade,
    ReportCard,
    ReportCardRemark,
    ReportCardStatus,
    ReportCardTemplate,
    TemplateBoard,
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
    LeaveApplication,
    LeaveStatus,
    Parent,
    ParentAccessLevel,
    ParentChildMapping,
    ParentSession,
    Relation,
    Student,
)
from app.models.sis import (  # noqa: F401
    Admission,
    AdmissionStage,
    Category,
    Gender,
    StudentDocument,
    StudentStatus,
)
from app.models.teacher import (  # noqa: F401
    AttendanceStatus,
    EmploymentStatus,
    Teacher,
    TeacherAttendance,
    TeacherSubject,
)
from app.models.timetable import (  # noqa: F401
    PeriodDef,
    Substitution,
    SubstitutionStatus,
    TimetableEntry,
)
from app.models.transport import (  # noqa: F401
    BoardingEvent,
    Bus,
    BusStatus,
    Driver,
    DriverStatus,
    FuelLog,
    MaintenanceKind,
    MaintenanceLog,
    Route,
    Stop,
    StudentTransport,
    Trip,
    TripBoarding,
    TripDirection,
    TripSkip,
    TripPhase,
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
from app.models.staff_extras import (  # noqa: F401
    BehaviourNote,
    BehaviourNoteKind,
    StaffLeave,
    StaffLeaveStatus,
)
from app.models.auth_extras import (  # noqa: F401
    PasswordResetOtp,
    UserDevice,
)
