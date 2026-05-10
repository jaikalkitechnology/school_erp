export type TenantStatus = "trial" | "active" | "suspended" | "cancelled";

export interface SubscriptionPlan {
  id: number;
  name: string;
  code: string;
  monthly_price: number;
  annual_price: number;
  student_limit: number;
  teacher_limit: number;
  storage_gb: number;
}

export interface Tenant {
  id: number;
  school_name: string;
  school_code: string;
  subdomain: string;
  city: string | null;
  state: string | null;
  status: TenantStatus;
  primary_color: string;
  secondary_color: string;
  student_limit: number;
  teacher_limit: number;
  storage_limit_mb: number;
  subscription_start: string | null;
  subscription_end: string | null;
  created_at: string;
  plan?: SubscriptionPlan | null;
}

export interface CreateTenantPayload {
  school_name: string;
  school_code: string;
  subdomain: string;
  plan_code: string;
  city?: string;
  state?: string;
  affiliation_board?: string;
  medium?: string;
}
