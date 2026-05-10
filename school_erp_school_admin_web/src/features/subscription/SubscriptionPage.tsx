import { useQuery } from "@tanstack/react-query";
import { CreditCard } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { mySubscription, type InvoiceStatus } from "./api";

const STATUS_TONE: Record<InvoiceStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  pending: "bg-marigold-pale text-marigold-dark",
  partial: "bg-saffron-pale text-saffron-darker",
  paid: "bg-teal-pale text-teal-dark",
  void: "bg-muted text-muted-foreground line-through",
  refunded: "bg-destructive/15 text-destructive",
};

export function SubscriptionPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-subscription"],
    queryFn: mySubscription,
  });
  if (isLoading || !data) return null;
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 21 · Subscription
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">My subscription</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          The plan your school is on, the next renewal date, and your platform invoice
          history. Plan changes are handled by Jaikalki — contact your account manager.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-saffron" />
              {data.plan_name ?? "No active plan"}
            </CardTitle>
            <CardDescription>Code: {data.plan_code ?? "—"}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-display text-indigo-dark">
              ₹{data.monthly_price ?? 0}
              <span className="text-sm text-muted-foreground"> / month</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Subscription status</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium text-indigo-dark">{data.status}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {data.subscription_start && `Since ${new Date(data.subscription_start).toLocaleDateString()}`}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Renews on</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-display text-indigo-dark">
              {data.subscription_end
                ? new Date(data.subscription_end).toLocaleDateString()
                : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invoice history</CardTitle>
          <CardDescription>{data.invoices.length} invoices</CardDescription>
        </CardHeader>
        <CardContent>
          {data.invoices.length === 0 ? (
            <p className="text-sm text-muted-foreground">No invoices yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Invoice #</th>
                  <th>Period</th>
                  <th>Issued</th>
                  <th>Due</th>
                  <th>Total</th>
                  <th>Paid</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.invoices.map((i) => (
                  <tr key={i.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-mono text-xs">{i.invoice_number}</td>
                    <td className="text-xs text-muted-foreground">
                      {i.period_start} → {i.period_end}
                    </td>
                    <td>{i.issued_on}</td>
                    <td>{i.due_date}</td>
                    <td>₹{i.total_amount}</td>
                    <td>₹{i.paid_amount}</td>
                    <td>
                      <span className={cn("rounded px-2 py-0.5 text-xs", STATUS_TONE[i.status])}>
                        {i.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
