import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { RecipientPicker } from "@/components/RecipientPicker";

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
    resets: ["recipient_user_ids"],
  },
  {
    key: "recipient_user_ids",
    label: "Send to",
    kind: "json",
    renderInput: ({ value, values, onChange, invalid }) => (
      <RecipientPicker audience={values.audience} value={value} onChange={onChange} invalid={invalid} />
    ),
    validate: (raw) => (raw === "[]" ? "Pick at least one person, or choose All." : null),
    render: (row) => {
      const ids = Array.isArray(row.recipient_user_ids) ? row.recipient_user_ids : [];
      if (ids.length) return `${ids.length} ${ids.length === 1 ? "person" : "people"}`;
      return row.audience && row.audience !== "all" ? `All ${row.audience}` : "Everyone";
    },
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
