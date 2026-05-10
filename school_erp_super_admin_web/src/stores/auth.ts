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
  full_name: string;
  email: string | null;
  phone: string | null;
  tenant_id: number;
  tenant_subdomain: string | null;
  school_name: string | null;
  roles: Role[];
  permissions: string[];
  primary_role: Role | null;
}

interface Tokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface AuthState {
  user: AuthUser | null;
  tokens: Tokens | null;
  setSession: (user: AuthUser, tokens: Tokens) => void;
  setTokens: (tokens: Tokens) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      tokens: null,
      setSession: (user, tokens) => {
        localStorage.setItem("jaikalki.access_token", tokens.access_token);
        set({ user, tokens });
      },
      setTokens: (tokens) => {
        localStorage.setItem("jaikalki.access_token", tokens.access_token);
        set({ tokens });
      },
      clear: () => {
        localStorage.removeItem("jaikalki.access_token");
        set({ user: null, tokens: null });
      },
    }),
    { name: "jaikalki.super-admin.auth" },
  ),
);
