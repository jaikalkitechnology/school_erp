import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { fetchVendorOptions } from "./_pickers";

const VENDOR_FIELDS: FieldSpec[] = [
  { key: "name", label: "Vendor", required: true },
  { key: "contact_person", label: "Contact" },
  { key: "phone", label: "Phone", kind: "phone" },
  { key: "email", label: "Email", kind: "email" },
  { key: "gst_number", label: "GST", hideInList: true },
  { key: "address", label: "Address", kind: "textarea", hideInList: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
  { key: "is_active", label: "Active", kind: "checkbox" },
];

const EXPENSE_FIELDS: FieldSpec[] = [
  { key: "category", label: "Category", required: true, placeholder: "salaries / utilities / stationery" },
  { key: "vendor_id", label: "Vendor", kind: "picker", fetchOptions: fetchVendorOptions, placeholder: "Pick a vendor (optional)" },
  { key: "amount", label: "Amount ₹", kind: "number", required: true },
  { key: "spent_on", label: "Date", kind: "date", required: true },
  { key: "paid_from", label: "Paid from", placeholder: "cash / bank / upi" },
  { key: "invoice_ref", label: "Invoice ref", hideInList: true },
  { key: "description", label: "Description", kind: "textarea", hideInList: true },
  {
    key: "status",
    label: "Status",
    kind: "select",
    options: [
      { value: "pending", label: "Pending" },
      { value: "approved", label: "Approved" },
      { value: "paid", label: "Paid" },
      { value: "rejected", label: "Rejected" },
    ],
  },
];

export function VendorsPage() {
  return (
    <SimpleCrudPage
      title="Vendors"
      subtitle="Suppliers you buy from — books, stationery, IT gear, chemicals. Link expenses to a vendor to see spend by supplier."
      endpoint="/v1/operations/vendors"
      queryKey="operations-vendors"
      fields={VENDOR_FIELDS}
    />
  );
}

export function ExpensesPage() {
  const { data: summary } = useQuery({
    queryKey: ["operations-finance-summary"],
    queryFn: () =>
      api.get<{
        month: string;
        income_month: number;
        expenses_month: number;
        expenses_pending: number;
        net_month: number;
      }>("/v1/operations/finance/summary").then((r) => r.data),
  });
  const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });
  return (
    <SimpleCrudPage
      title="Expenses"
      subtitle="Every outgoing rupee. Fees stays the incoming side; this is the other half of your P&L."
      endpoint="/v1/operations/expenses"
      queryKey="operations-expenses"
      fields={EXPENSE_FIELDS}
      extraTop={
        summary ? (
          <div className="grid gap-2 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Income · MTD</p>
                <p className="mt-1 font-display text-2xl text-teal-dark">{inr.format(summary.income_month)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Expenses · MTD</p>
                <p className="mt-1 font-display text-2xl text-saffron-darker">{inr.format(summary.expenses_month)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Pending approval</p>
                <p className="mt-1 font-display text-2xl text-marigold-dark">{inr.format(summary.expenses_pending)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Net · MTD</p>
                <p className={`mt-1 font-display text-2xl ${summary.net_month >= 0 ? "text-teal-dark" : "text-destructive"}`}>
                  {inr.format(summary.net_month)}
                </p>
              </CardContent>
            </Card>
          </div>
        ) : null
      }
    />
  );
}
