import { Navigate, type RouteObject } from "react-router-dom";
import { SchoolAdminLayout } from "@/components/layouts/SchoolAdminLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { Placeholder } from "@/features/placeholder/Placeholder";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { CommunicationPage } from "@/features/communication/CommunicationPage";
import { CurriculumPage } from "@/features/curriculum/CurriculumPage";
import { ExamsPage } from "@/features/exams/ExamsPage";
import { FeesPage } from "@/features/fees/FeesPage";
import { ReportCardsPage } from "@/features/report_cards/ReportCardsPage";
import { HomeworkPage } from "@/features/homework/HomeworkPage";
import { LibraryPage } from "@/features/library/LibraryPage";
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
      { path: "attendance", element: <AttendancePage /> },
      { path: "timetable", element: <TimetablePage /> },
      { path: "homework", element: <HomeworkPage /> },
      { path: "exams", element: <ExamsPage /> },
      { path: "report-cards", element: <ReportCardsPage /> },
      { path: "fees", element: <FeesPage /> },
      { path: "communication", element: <CommunicationPage /> },
      { path: "library", element: <LibraryPage /> },
      { path: "transport", element: <TransportPage /> },
      { path: "hostel", element: <HostelPage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "subscription", element: <SubscriptionPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
