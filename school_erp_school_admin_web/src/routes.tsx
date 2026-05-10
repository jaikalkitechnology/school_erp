import { Navigate, type RouteObject } from "react-router-dom";
import { SchoolAdminLayout } from "@/components/layouts/SchoolAdminLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { Placeholder } from "@/features/placeholder/Placeholder";
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
      { path: "students", element: <Placeholder title="Students" phase="Phase 6 (SIS)" /> },
      { path: "teachers", element: <Placeholder title="Teachers" phase="Phase 7 (Teacher Management)" /> },
      { path: "attendance", element: <Placeholder title="Attendance" phase="Phase 9 (Attendance)" /> },
      { path: "timetable", element: <Placeholder title="Timetable" phase="Phase 13 (Timetable & Substitution)" /> },
      { path: "exams", element: <Placeholder title="Exams" phase="Phase 15 (Examination System)" /> },
      { path: "fees", element: <Placeholder title="Fees" phase="Phase 11 (Fee Management)" /> },
      { path: "communication", element: <Placeholder title="Communication" phase="Phase 12 (Communication)" /> },
      { path: "library", element: <Placeholder title="Library" phase="Phase 17 (Library)" /> },
      { path: "transport", element: <Placeholder title="Transport" phase="Phase 18 (Transport + GPS)" /> },
      { path: "settings", element: <Placeholder title="Settings" phase="Phase 4 (School Admin Foundation)" /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
