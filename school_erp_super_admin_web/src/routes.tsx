import { Navigate, type RouteObject } from "react-router-dom";
import { SuperAdminLayout } from "@/components/layouts/SuperAdminLayout";
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
        <SuperAdminLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "schools", element: <Placeholder title="Schools" phase="Phase 3 (Super Admin onboarding)" /> },
      { path: "plans", element: <Placeholder title="Plans & Billing" phase="Phase 21 (Subscription & Billing)" /> },
      { path: "staff", element: <Placeholder title="Platform Staff" phase="Phase 2 (Auth & RBAC)" /> },
      { path: "audit", element: <Placeholder title="Audit & Security" phase="Phase 22 (Final hardening)" /> },
      { path: "settings", element: <Placeholder title="Platform Settings" phase="Phase 1 (Multi-tenant)" /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
