import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { fetchStudentOptions } from "./_pickers";

const FIELDS: FieldSpec[] = [
  { key: "full_name", label: "Name", required: true },
  { key: "graduation_year", label: "Batch", kind: "number", required: true },
  { key: "current_role", label: "Role" },
  { key: "current_company", label: "Company" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "city", label: "City" },
  { key: "linkedin_url", label: "LinkedIn URL", hideInList: true },
  { key: "student_id", label: "Original student record", kind: "picker", fetchOptions: fetchStudentOptions, hideInList: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

export function AlumniPage() {
  return (
    <SimpleCrudPage
      title="Alumni directory"
      subtitle="Ex-students. Track batch, current role, and contact so you can invite them to reunions, mentorship, or fund drives."
      endpoint="/v1/operations/alumni"
      queryKey="operations-alumni"
      fields={FIELDS}
    />
  );
}
