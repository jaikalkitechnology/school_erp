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
import { LibraryStub } from "@/features/library/LibraryStub";
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
      {
        path: "library-authors",
        element: (
          <LibraryStub
            title="Authors"
            subtitle="Registry of the people who wrote the books in the catalogue."
            planned={[
              "Searchable list of every author across the catalogue",
              "Merge duplicate author records (same person, different spellings)",
              "Bio, portrait, and works-in-catalogue counts per author",
              "Filter the Books tab by any author with one click",
            ]}
          />
        ),
      },
      {
        path: "library-publishers",
        element: (
          <LibraryStub
            title="Publishers"
            subtitle="Every publishing house whose titles are on the shelves."
            planned={[
              "Publisher directory with contact + address",
              "Titles per publisher with quick jump to the Books list",
              "Track supplier discount + turnaround time for reordering",
            ]}
          />
        ),
      },
      {
        path: "library-shelves",
        element: (
          <LibraryStub
            title="Shelves & racks"
            subtitle="Physical location map — which rack / shelf a given copy lives on."
            planned={[
              "Rack → shelf hierarchy per section of the library",
              "Assign a copy to a shelf via barcode scan",
              "Print shelf labels + call-number stickers in one click",
              "Auto-suggest a shelf when accessioning a new title",
            ]}
          />
        ),
      },
      { path: "library-issue", element: <LibraryIssueBooksPage /> },
      { path: "library-return", element: <LibraryReturnBooksPage /> },
      {
        path: "library-renew",
        element: (
          <LibraryStub
            title="Renew books"
            subtitle="Extend the due date on an active loan without a full return-then-reissue."
            planned={[
              "Look up a loan by borrower or copy barcode",
              "Preview the new due date before confirming",
              "Cap max renewals per policy (eg. 2 renewals per loan)",
              "Block renewal if another borrower has reserved the title",
            ]}
          />
        ),
      },
      { path: "library-reservations", element: <LibraryReservationsPage /> },
      { path: "library-fines", element: <LibraryFineManagementPage /> },
      { path: "library-lost", element: <LibraryLostDamagedPage /> },
      {
        path: "library-inventory",
        element: (
          <LibraryStub
            title="Inventory verification"
            subtitle="Annual stock-take — walk the shelves, scan every barcode, reconcile against the catalogue."
            planned={[
              "Start a verification session tied to a date + auditor",
              "Handheld / phone barcode scan updates the session in real time",
              "Missing / mis-shelved report at session close",
              "Bulk-mark missing copies as 'lost' with one click",
            ]}
          />
        ),
      },
      {
        path: "library-barcode",
        element: (
          <LibraryStub
            title="Barcode management"
            subtitle="Generate, print, and manage the barcode labels for every copy."
            planned={[
              "Bulk-print barcode stickers for a batch of accession numbers",
              "Regenerate + reprint a damaged sticker without changing the copy ID",
              "Barcode format switcher (Code 128 / EAN-13 / QR)",
              "Test-scan reader with live feedback",
            ]}
          />
        ),
      },
      { path: "library-reports", element: <LibraryReportsPage /> },
      {
        path: "library-import-export",
        element: (
          <LibraryStub
            title="Import / export"
            subtitle="Bulk data in and out. Onboarding a new library or backing up the catalogue."
            planned={[
              "Import books + copies from a CSV / Excel template",
              "Import from MARC records (standard library exchange format)",
              "Export the full catalogue + circulation history to CSV or JSON",
              "Snapshot download for offline audit",
            ]}
          />
        ),
      },
      {
        path: "library-notifications",
        element: (
          <LibraryStub
            title="Notifications"
            subtitle="Automated messages to borrowers — due-soon reminders, reservation-ready alerts, fine notices."
            planned={[
              "Due-in-2-days SMS / push to every borrower",
              "Reservation-is-ready notice when a copy comes back",
              "Overdue escalation (day 1, day 7, day 14) with rising urgency",
              "Templates editable per school, previewable per role",
            ]}
          />
        ),
      },
      { path: "library-user-history", element: <LibraryUserHistoryPage /> },
      {
        path: "library-audit",
        element: (
          <LibraryStub
            title="Audit logs"
            subtitle="Immutable trail of every action taken in the library module — who did what, when, and to which copy."
            planned={[
              "Filter by user, date range, action type, or affected copy",
              "Show diffs on record edits (title change, fine adjustment, etc.)",
              "Export any window to CSV for external audit",
              "Retention window enforced (12 months by default)",
            ]}
          />
        ),
      },
      {
        path: "library-settings",
        element: (
          <LibraryStub
            title="Library settings"
            subtitle="Module-wide defaults — loan lengths, fine rates, reservation policy, opening hours."
            planned={[
              "Default loan days + fine-per-day per borrower type",
              "Reservation queue policy (max per borrower, expiry)",
              "Library opening hours + closed dates (feeds fine calc)",
              "Notification opt-in toggles (SMS / email / push)",
            ]}
          />
        ),
      },
      { path: "transport", element: <TransportPage /> },
      { path: "hostel", element: <HostelPage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "subscription", element: <SubscriptionPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
