import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileText, Play } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { SimpleCrudPage, type FieldSpec } from "./_crud";
import { fetchStaffUserOptions } from "./_pickers";

const STRUCT_FIELDS: FieldSpec[] = [
  { key: "user_id", label: "Staff member", kind: "picker", fetchOptions: fetchStaffUserOptions, required: true },
  { key: "basic", label: "Basic", kind: "number", required: true },
  { key: "hra", label: "HRA", kind: "number" },
  { key: "effective_from", label: "Effective from", kind: "date", required: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

export function SalaryStructuresPage() {
  return (
    <SimpleCrudPage
      title="Salary structures"
      subtitle="One row per staff member. Payslips are generated off the latest structure effective on the pay date. Allowances and deductions live on the row as JSON (edit via API for now)."
      endpoint="/v1/operations/salary-structures"
      queryKey="operations-salary-structures"
      fields={STRUCT_FIELDS}
    />
  );
}

interface Payslip {
  id: number;
  user_id: number;
  period: string;
  basic: number;
  hra: number;
  other_earnings: number;
  total_deductions: number;
  net_pay: number;
  status: string;
  paid_on: string | null;
}

export function PayslipsPage() {
  const qc = useQueryClient();
  const [userId, setUserId] = useState("");
  const [period, setPeriod] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

  const { data: rows = [] } = useQuery({
    queryKey: ["operations-payslips"],
    queryFn: () => api.get<Payslip[]>("/v1/operations/payslips").then((r) => r.data),
  });

  const gen = useMutation({
    mutationFn: () =>
      api.post("/v1/operations/payslips/generate", {
        user_id: Number(userId),
        period,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operations-payslips"] });
      setUserId("");
      setPeriod("");
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Generate failed.");
    },
  });

  const markPaid = useMutation({
    mutationFn: (id: number) => api.post(`/v1/operations/payslips/${id}/mark-paid`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operations-payslips"] }),
  });

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations · Payroll
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Payslips</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Generate a payslip for a staff member for a given month. Reads the
          latest salary structure and computes gross + deductions + net.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Generate payslip</CardTitle>
          <CardDescription>Fails if a slip already exists for the same user + period.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <Label>User #</Label>
            <Input value={userId} onChange={(e) => setUserId(e.target.value)} />
          </div>
          <div>
            <Label>Period (YYYY-MM)</Label>
            <Input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="2026-07" />
          </div>
          <div className="flex items-end">
            <Button onClick={() => gen.mutate()} disabled={!userId || !period || gen.isPending}>
              <Play className="mr-1 h-4 w-4" /> Generate
            </Button>
          </div>
          {errorMsg && (
            <p className="col-span-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Payslips</CardTitle>
          <CardDescription>{rows.length} on record</CardDescription>
        </CardHeader>
        <CardContent>
          {rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing yet. Generate one above.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Period</th>
                  <th>User</th>
                  <th>Basic</th>
                  <th>HRA</th>
                  <th>Other</th>
                  <th>Deductions</th>
                  <th>Net</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-mono">{r.period}</td>
                    <td>#{r.user_id}</td>
                    <td>{inr.format(Number(r.basic))}</td>
                    <td>{inr.format(Number(r.hra))}</td>
                    <td>{inr.format(Number(r.other_earnings))}</td>
                    <td>{inr.format(Number(r.total_deductions))}</td>
                    <td className="font-semibold text-teal-dark">
                      {inr.format(Number(r.net_pay))}
                    </td>
                    <td>
                      <span
                        className={cn(
                          "rounded px-2 py-0.5 text-xs",
                          r.status === "paid"
                            ? "bg-teal-pale text-teal-dark"
                            : r.status === "issued"
                            ? "bg-marigold-pale text-marigold-dark"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="text-right">
                      {r.status !== "paid" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => markPaid.mutate(r.id)}
                        >
                          <CheckCircle2 className="mr-1 h-3 w-3" /> Mark paid
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => window.print()}
                      >
                        <FileText className="mr-1 h-3 w-3" /> Print
                      </Button>
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
