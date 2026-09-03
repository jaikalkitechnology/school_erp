import { api } from "@/lib/api";
import { listStudents } from "@/features/students/api";
import { listTeachers } from "@/features/teachers/api";
import type { PickerOption } from "./_crud";

/** Fetchers used by the FK picker fields. Each returns the shape
 * ``PickerOption[]`` — id + human label + optional hint (extra
 * context shown under the label). */

export const fetchVendorOptions = async (): Promise<PickerOption[]> => {
  const rows = await api
    .get<Array<{ id: number; name: string; phone: string | null }>>(
      "/v1/operations/vendors",
    )
    .then((r) => r.data);
  return rows.map((v) => ({
    id: v.id,
    label: v.name,
    hint: v.phone ?? undefined,
  }));
};

export const fetchInventoryItemOptions = async (): Promise<PickerOption[]> => {
  const rows = await api
    .get<Array<{ id: number; name: string; code: string; on_hand: number; unit: string }>>(
      "/v1/operations/inventory-items",
    )
    .then((r) => r.data);
  return rows.map((i) => ({
    id: i.id,
    label: i.name,
    hint: `${i.code} · ${i.on_hand} ${i.unit} on hand`,
  }));
};

export const fetchSportsHouseOptions = async (): Promise<PickerOption[]> => {
  const rows = await api
    .get<Array<{ id: number; name: string; points: number }>>(
      "/v1/operations/sports-houses",
    )
    .then((r) => r.data);
  return rows.map((h) => ({
    id: h.id,
    label: h.name,
    hint: `${h.points} pts`,
  }));
};

/** Student picker — up to 200 active students. For schools with more
 * students, the UI still lets you type-search the fetched list. If we
 * ever need pagination inside the dropdown, this is the place. */
export const fetchStudentOptions = async (): Promise<PickerOption[]> => {
  const res = await listStudents({ limit: 200 });
  return res.items.map((s) => ({
    id: s.id,
    label: s.full_name,
    hint: `${s.admission_number}${
      s.current_class_label ? ` · ${s.current_class_label}` : ""
    }`,
  }));
};

/** Teacher picker — returns Teacher.id (not user id), which is the id
 * space the library borrower / other teacher FKs expect. */
export const fetchTeacherOptions = async (): Promise<PickerOption[]> => {
  const res = await listTeachers({ limit: 200 });
  return res.items.map((t) => ({
    id: t.id,
    label: t.full_name,
    hint: [t.employee_no, t.designation ?? undefined].filter(Boolean).join(" · ") || undefined,
  }));
};

/** Staff-user picker — every active user account in the tenant, which
 * includes teachers (onboarding a teacher creates a User row). Used
 * for salary structures, payslip target, visitor host, etc. The
 * salary/payslip FK is users.id, so this is the correct source.
 *
 * Uses the dedicated /operations/_staff-options endpoint (gated to
 * the broad operations-staff role set) rather than the full
 * /school-admin/users admin surface — so a payroll / accounts user
 * who can see the Salary page can also populate this dropdown. */
export const fetchStaffUserOptions = async (): Promise<PickerOption[]> => {
  try {
    const rows = await api
      .get<Array<{ id: number; full_name: string; email: string | null; role_codes: string[] }>>(
        "/v1/operations/_staff-options",
      )
      .then((r) => r.data);
    return rows.map((u) => ({
      id: u.id,
      label: u.full_name,
      hint: [u.email, (u.role_codes ?? []).join(", ")].filter(Boolean).join(" · "),
    }));
  } catch {
    return [];
  }
};
