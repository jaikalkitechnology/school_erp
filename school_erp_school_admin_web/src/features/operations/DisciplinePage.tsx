import { SimpleCrudPage, type FieldSpec } from "./_crud";

const FIELDS: FieldSpec[] = [
  { key: "student_id", label: "Student #", kind: "number", required: true },
  { key: "occurred_on", label: "Date", kind: "date", required: true },
  { key: "location", label: "Location" },
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
  { key: "headline", label: "Headline", required: true },
  { key: "description", label: "What happened", kind: "textarea", hideInList: true },
  { key: "action_taken", label: "Action taken", kind: "textarea", hideInList: true },
  { key: "parent_informed", label: "Parent informed", kind: "checkbox" },
];

export function DisciplinePage() {
  return (
    <SimpleCrudPage
      title="Discipline incidents"
      subtitle="Serious behavioural incidents — bullying, cheating, damage, absconding. This is the escalated register; day-to-day behaviour notes stay on the mobile teacher app."
      endpoint="/v1/operations/discipline-incidents"
      queryKey="operations-discipline-incidents"
      fields={FIELDS}
    />
  );
}
