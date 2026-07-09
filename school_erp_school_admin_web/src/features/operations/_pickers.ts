import { api } from "@/lib/api";
import { listStudents } from "@/features/students/api";
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

/** Staff-user picker (any user with a staff-ish role assigned). Used
 * for salary structures, payslip target, visitor host, etc. */
export const fetchStaffUserOptions = async (): Promise<PickerOption[]> => {
  // Reuse the admin users listing endpoint if it exists; otherwise
  // fall back to a lightweight all-users listing.
  try {
    const page = await api
      .get<{ items: Array<{ id: number; full_name: string; email: string | null; role_codes: string[] }> }>(
        "/v1/school-admin/users",
        { params: { limit: 500 } },
      )
      .then((r) => r.data);
    return (page.items ?? []).map((u) => ({
      id: u.id,
      label: u.full_name,
      hint: [u.email, u.role_codes.join(", ")].filter(Boolean).join(" · "),
    }));
  } catch {
    return [];
  }
};
