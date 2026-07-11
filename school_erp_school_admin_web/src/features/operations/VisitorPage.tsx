import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { fetchStaffUserOptions } from "./_pickers";

const FIELDS: FieldSpec[] = [
  { key: "full_name", label: "Visitor", required: true },
  { key: "phone", label: "Phone", kind: "phone" },
  { key: "company", label: "Company / from" },
  { key: "purpose", label: "Purpose", placeholder: "meeting / delivery / fee payment" },
  { key: "host_user_id", label: "Host (staff)", kind: "picker", fetchOptions: fetchStaffUserOptions, hideInList: true },
  { key: "id_proof_type", label: "ID type", placeholder: "aadhaar / dl / other", hideInList: true },
  { key: "id_proof_ref", label: "ID number", hideInList: true },
  { key: "badge_no", label: "Badge #" },
  { key: "checked_in_at", label: "Checked in", kind: "datetime", hideInForm: true },
  { key: "checked_out_at", label: "Checked out", kind: "datetime", hideInForm: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

export function VisitorPage() {
  const qc = useQueryClient();
  const checkout = useMutation({
    mutationFn: (id: number) => api.post(`/v1/operations/visitor-logs/${id}/checkout`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operations-visitor-logs"] }),
  });
  return (
    <SimpleCrudPage
      title="Visitor logs"
      subtitle="Every walk-in — parents, vendors, contractors. Check them out when they leave; the check-in time is stamped automatically on Add."
      endpoint="/v1/operations/visitor-logs"
      queryKey="operations-visitor-logs"
      fields={FIELDS}
      extraActions={(row) =>
        !row.checked_out_at ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => checkout.mutate(Number(row.id))}
          >
            <LogOut className="mr-1 h-3 w-3" /> Check out
          </Button>
        ) : null
      }
    />
  );
}
