import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role =
  | "super_admin"
  | "school_admin"
  | "principal"
  | "vice_principal"
  | "coordinator"
  | "class_teacher"
  | "subject_teacher"
  | "accountant"
  | "librarian"
  | "transport_manager"
  | "hostel_warden"
  | "office_staff"
  | "parent"
  | "student";

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  roles: Role[];
  tenant_id: number | null;
  tenant_subdomain: string | null;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  setSession: (user: AuthUser, accessToken: string) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      setSession: (user, accessToken) => {
        localStorage.setItem("jaikalki.access_token", accessToken);
        set({ user, accessToken });
      },
      clear: () => {
        localStorage.removeItem("jaikalki.access_token");
        set({ user: null, accessToken: null });
      },
    }),
    { name: "jaikalki.super-admin.auth" },
  ),
);
