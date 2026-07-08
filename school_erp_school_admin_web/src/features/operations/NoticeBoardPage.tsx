import { SimpleCrudPage, type FieldSpec } from "./_crud";

const FIELDS: FieldSpec[] = [
  { key: "title", label: "Title", required: true },
  {
    key: "audience",
    label: "Audience",
    kind: "select",
    options: [
      { value: "all", label: "Everyone" },
      { value: "staff", label: "Staff only" },
      { value: "parents", label: "Parents" },
      { value: "students", label: "Students" },
    ],
  },
  { key: "is_pinned", label: "Pinned", kind: "checkbox" },
  { key: "published_at", label: "Publish at", kind: "datetime" },
  { key: "expires_at", label: "Expires at", kind: "datetime", hideInList: true },
  { key: "body", label: "Body", kind: "textarea", hideInList: true },
];

export function NoticeBoardPage() {
  return (
    <SimpleCrudPage
      title="Notice board"
      subtitle="Static bulletins — closure notices, calendar changes, exam rules. Different from Communication push messages: notices are long-lived and live on the mobile app's Notice tab."
      endpoint="/v1/operations/notices"
      queryKey="operations-notices"
      fields={FIELDS}
    />
  );
}
