import { Navigate, type RouteObject } from "react-router-dom";
import { SchoolAdminLayout } from "@/components/layouts/SchoolAdminLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { CommunicationPage } from "@/features/communication/CommunicationPage";
import { CurriculumPage } from "@/features/curriculum/CurriculumPage";
import { ExamsPage } from "@/features/exams/ExamsPage";
import { FeesPage } from "@/features/fees/FeesPage";
import { ReportCardsPage } from "@/features/report_cards/ReportCardsPage";
import { HomeworkPage } from "@/features/homework/HomeworkPage";
import { LibraryDashboardPage } from "@/features/library/LibraryDashboardPage";
import { LibraryBooksPage } from "@/features/library/LibraryBooksPage";
import { LibraryCategoriesPage } from "@/features/library/LibraryCategoriesPage";
import { LibraryBookCopiesPage } from "@/features/library/LibraryBookCopiesPage";
import { LibraryIssueBooksPage } from "@/features/library/LibraryIssueBooksPage";
import { LibraryReturnBooksPage } from "@/features/library/LibraryReturnBooksPage";
import { LibraryFineManagementPage } from "@/features/library/LibraryFineManagementPage";
import { LibraryReportsPage } from "@/features/library/LibraryReportsPage";
import { LibraryReservationsPage } from "@/features/library/LibraryReservationsPage";
import { LibraryLostDamagedPage } from "@/features/library/LibraryLostDamagedPage";
import { LibraryUserHistoryPage } from "@/features/library/LibraryUserHistoryPage";
// LibraryStub is retained in the codebase for future new sub-pages
// that want a quick placeholder — no live route uses it right now.
import { LibraryAuthorsPage } from "@/features/library/LibraryAuthorsPage";
import { LibraryPublishersPage } from "@/features/library/LibraryPublishersPage";
import { LibraryShelvesPage } from "@/features/library/LibraryShelvesPage";
import { LibraryRenewBooksPage } from "@/features/library/LibraryRenewBooksPage";
import { LibraryInventoryPage } from "@/features/library/LibraryInventoryPage";
import { LibraryBarcodePage } from "@/features/library/LibraryBarcodePage";
import { LibraryImportExportPage } from "@/features/library/LibraryImportExportPage";
import { LibraryNotificationsPage } from "@/features/library/LibraryNotificationsPage";
import { LibraryAuditPage } from "@/features/library/LibraryAuditPage";
import { LibrarySettingsPage } from "@/features/library/LibrarySettingsPage";
import { TimetablePage } from "@/features/timetable/TimetablePage";
import { TransportPage } from "@/features/transport/TransportPage";
import { HostelPage } from "@/features/hostel/HostelPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { SubscriptionPage } from "@/features/subscription/SubscriptionPage";
import { AcademicPage } from "@/features/setup/AcademicPage";
import { OrgPage } from "@/features/setup/OrgPage";
import { SettingsPage } from "@/features/setup/SettingsPage";
import { AdmitStudentPage } from "@/features/students/AdmitStudentPage";
import { StudentDetailPage } from "@/features/students/StudentDetailPage";
import { StudentsPage } from "@/features/students/StudentsPage";
import { OnboardTeacherPage } from "@/features/teachers/OnboardTeacherPage";
import { TeacherDetailPage } from "@/features/teachers/TeacherDetailPage";
import { TeachersPage } from "@/features/teachers/TeachersPage";
import { StaffPage } from "@/features/staff/StaffPage";
import { UsersPage } from "@/features/users/UsersPage";
import { useAuth } from "@/stores/auth";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuth((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <SchoolAdminLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "org", element: <OrgPage /> },
      { path: "academic", element: <AcademicPage /> },
      { path: "curriculum", element: <CurriculumPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "students", element: <StudentsPage /> },
      { path: "students/admit", element: <AdmitStudentPage /> },
      { path: "students/:id", element: <StudentDetailPage /> },
      { path: "teachers", element: <TeachersPage /> },
      { path: "teachers/onboard", element: <OnboardTeacherPage /> },
      { path: "teachers/:id", element: <TeacherDetailPage /> },
      { path: "staff", element: <StaffPage /> },
      { path: "users", element: <UsersPage /> },
      { path: "attendance", element: <AttendancePage /> },
      { path: "timetable", element: <TimetablePage /> },
      { path: "homework", element: <HomeworkPage /> },
      { path: "exams", element: <ExamsPage /> },
      { path: "report-cards", element: <ReportCardsPage /> },
      { path: "fees", element: <FeesPage /> },
      { path: "communication", element: <CommunicationPage /> },
      { path: "library", element: <LibraryDashboardPage /> },
      { path: "library-books", element: <LibraryBooksPage /> },
      { path: "library-copies", element: <LibraryBookCopiesPage /> },
      { path: "library-categories", element: <LibraryCategoriesPage /> },
      { path: "library-authors", element: <LibraryAuthorsPage /> },
      { path: "library-publishers", element: <LibraryPublishersPage /> },
      { path: "library-shelves", element: <LibraryShelvesPage /> },
      { path: "library-issue", element: <LibraryIssueBooksPage /> },
      { path: "library-return", element: <LibraryReturnBooksPage /> },
      { path: "library-renew", element: <LibraryRenewBooksPage /> },
      { path: "library-reservations", element: <LibraryReservationsPage /> },
      { path: "library-fines", element: <LibraryFineManagementPage /> },
      { path: "library-lost", element: <LibraryLostDamagedPage /> },
      { path: "library-inventory", element: <LibraryInventoryPage /> },
      { path: "library-barcode", element: <LibraryBarcodePage /> },
      { path: "library-reports", element: <LibraryReportsPage /> },
      { path: "library-import-export", element: <LibraryImportExportPage /> },
      { path: "library-notifications", element: <LibraryNotificationsPage /> },
      { path: "library-user-history", element: <LibraryUserHistoryPage /> },
      { path: "library-audit", element: <LibraryAuditPage /> },
      { path: "library-settings", element: <LibrarySettingsPage /> },
      { path: "transport", element: <TransportPage /> },
      { path: "hostel", element: <HostelPage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "subscription", element: <SubscriptionPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
