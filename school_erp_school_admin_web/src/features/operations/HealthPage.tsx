import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { fetchStudentOptions } from "./_pickers";

const FIELDS: FieldSpec[] = [
  { key: "student_id", label: "Student", kind: "picker", fetchOptions: fetchStudentOptions, required: true },
  {
    key: "kind",
    label: "Kind",
    kind: "select",
    required: true,
    options: [
      { value: "visit", label: "Sick room visit" },
      { value: "vaccination", label: "Vaccination" },
      { value: "allergy", label: "Allergy note" },
      { value: "note", label: "General note" },
    ],
  },
  { key: "title", label: "Headline", required: true },
  { key: "occurred_on", label: "Date", kind: "date", required: true },
  {
    key: "severity",
    label: "Severity",
    kind: "select",
    options: [
      { value: "minor", label: "Minor" },
      { value: "moderate", label: "Moderate" },
      { value: "major", label: "Major" },
    ],
  },
  { key: "description", label: "Description", kind: "textarea" },
  { key: "treatment", label: "Treatment", kind: "textarea", hideInList: true },
  { key: "medication", label: "Medication", kind: "textarea", hideInList: true },
  { key: "follow_up_on", label: "Follow-up", kind: "date", hideInList: true },
];

export function HealthPage() {
  return (
    <SimpleCrudPage
      title="Health records"
      subtitle="Every sick-room visit, vaccination, allergy note. Parents can see their child's records via the mobile app when the health integration ships."
      endpoint="/v1/operations/health-records"
      queryKey="operations-health-records"
      fields={FIELDS}
    />
  );
}
