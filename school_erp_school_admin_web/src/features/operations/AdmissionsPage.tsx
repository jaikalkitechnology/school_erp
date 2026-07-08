import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { SimpleCrudPage, type FieldSpec } from "./_crud";

const STAGES = [
  { value: "enquiry", label: "Enquiry" },
  { value: "applied", label: "Applied" },
  { value: "tested", label: "Tested" },
  { value: "offered", label: "Offered" },
  { value: "confirmed", label: "Confirmed" },
  { value: "converted", label: "Converted (student)" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

const STAGE_TONE: Record<string, string> = {
  enquiry: "bg-muted text-muted-foreground",
  applied: "bg-marigold-pale text-marigold-dark",
  tested: "bg-marigold-pale text-marigold-dark",
  offered: "bg-teal-pale text-teal-dark",
  confirmed: "bg-teal-pale text-teal-dark",
  converted: "bg-teal-pale text-teal-dark",
  rejected: "bg-destructive/15 text-destructive",
  withdrawn: "bg-destructive/15 text-destructive",
};

const FIELDS: FieldSpec[] = [
  { key: "child_full_name", label: "Child name", required: true },
  { key: "class_applying_for", label: "Class" },
  { key: "parent_name", label: "Parent" },
  { key: "parent_phone", label: "Phone" },
  { key: "parent_email", label: "Email", hideInList: true },
  { key: "child_dob", label: "DOB", kind: "date", hideInList: true },
  { key: "source", label: "Source", placeholder: "walk-in / website / referral", hideInList: true },
  {
    key: "stage",
    label: "Stage",
    kind: "select",
    options: STAGES,
    render: (r) => (
      <span
        className={cn(
          "rounded px-2 py-0.5 text-xs",
          STAGE_TONE[String(r.stage)] ?? "bg-muted",
        )}
      >
        {String(r.stage ?? "—")}
      </span>
    ),
  },
  { key: "test_date", label: "Test date", kind: "date", hideInList: true },
  { key: "test_score", label: "Score", kind: "number", hideInList: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

export function AdmissionsPage() {
  const { data: stats } = useQuery({
    queryKey: ["operations-admissions-stats"],
    queryFn: () => api.get<Record<string, number>>("/v1/operations/admissions/stats").then((r) => r.data),
  });
  return (
    <SimpleCrudPage
      title="Admissions"
      subtitle="Track every prospective family through the pipeline — enquiry, applied, tested, offered, confirmed, converted."
      endpoint="/v1/operations/admissions"
      queryKey="operations-admissions"
      fields={FIELDS}
      extraTop={
        stats && Object.keys(stats).length > 0 ? (
          <div className="grid gap-2 md:grid-cols-4">
            {STAGES.map((s) => (
              <Card key={s.value}>
                <CardContent className="p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    {s.label}
                  </p>
                  <p className="mt-1 text-2xl font-display text-indigo-dark">
                    {stats[s.value] ?? 0}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : null
      }
    />
  );
}
