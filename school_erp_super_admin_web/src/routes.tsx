import { Navigate, type RouteObject } from "react-router-dom";
import { SuperAdminLayout } from "@/components/layouts/SuperAdminLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { Placeholder } from "@/features/placeholder/Placeholder";
import { AuditPage } from "@/features/audit/AuditPage";
import { BillingPage } from "@/features/billing/BillingPage";
import { PlansPage } from "@/features/plans/PlansPage";
import { OnboardingWizard } from "@/features/schools/OnboardingWizard";
import { SchoolsPage } from "@/features/schools/SchoolsPage";
import { TenantDetailPage } from "@/features/schools/TenantDetailPage";
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
      { path: "schools", element: <SchoolsPage /> },
      { path: "schools/new", element: <OnboardingWizard /> },
      { path: "schools/:id", element: <TenantDetailPage /> },
      { path: "plans", element: <PlansPage /> },
      { path: "billing", element: <BillingPage /> },
      { path: "staff", element: <Placeholder title="Platform Staff" phase="Phase 4 (school admin foundation)" /> },
      { path: "audit", element: <AuditPage /> },
      { path: "settings", element: <Placeholder title="Platform Settings" phase="Phase 3.8 (system config)" /> },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
];
