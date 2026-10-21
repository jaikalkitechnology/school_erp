import { api } from "@/lib/api";

/** School name + logo for the signed-in user's school (any role). */
export interface Branding {
  school_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
}

export const fetchBranding = async () =>
  (await api.get<Branding>("/v1/auth/branding")).data;

/** Uploads a logo image and returns the stored path to save as logo_url. */
export const uploadSchoolLogo = async (file: File): Promise<string> => {
  const form = new FormData();
  form.append("file", file);
  form.append("category", "school");
  form.append("subcategory", "branding"); // PNG, JPG or SVG
  const res = await api.post<{ path: string }>("/v1/uploads", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data.path;
};
