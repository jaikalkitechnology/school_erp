import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Printer, Send } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SimpleCrudPage, type FieldSpec } from "./_crud";

const TEMPLATE_FIELDS: FieldSpec[] = [
  { key: "code", label: "Code", required: true, placeholder: "bonafide / tc / character" },
  { key: "name", label: "Name", required: true },
  { key: "signatory_label", label: "Signatory" },
  {
    key: "body_html",
    label: "Body (HTML with {{placeholders}})",
    kind: "textarea",
    hideInList: true,
    placeholder: "This is to certify that {{name}} of class {{class}} …",
  },
  { key: "is_active", label: "Active", kind: "checkbox" },
];

export function CertificateTemplatesPage() {
  return (
    <SimpleCrudPage
      title="Certificate templates"
      subtitle="Bonafide, TC (transfer), character, conduct, migration. Body uses {{key}} placeholders — fill them in when you issue."
      endpoint="/v1/operations/certificate-templates"
      queryKey="operations-certificate-templates"
      fields={TEMPLATE_FIELDS}
    />
  );
}

interface Template {
  id: number;
  code: string;
  name: string;
  body_html: string;
  is_active: boolean;
}

interface Issued {
  id: number;
  template_code: string;
  for_name: string;
  reference_no: string;
  issued_on: string;
  rendered_body: string;
}

export function IssueCertificatePage() {
  const qc = useQueryClient();
  const { data: templates = [] } = useQuery({
    queryKey: ["operations-certificate-templates"],
    queryFn: () =>
      api.get<Template[]>("/v1/operations/certificate-templates").then((r) => r.data),
  });
  const { data: issued = [] } = useQuery({
    queryKey: ["operations-issued-certificates"],
    queryFn: () =>
      api.get<Issued[]>("/v1/operations/issued-certificates").then((r) => r.data),
  });

  const [code, setCode] = useState("");
  const [forName, setForName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [context, setContext] = useState<string>('{\n  "name": "",\n  "class": "",\n  "session": "2026-27"\n}');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [preview, setPreview] = useState<Issued | null>(null);

  const issue = useMutation({
    mutationFn: () => {
      let ctx: Record<string, unknown> = {};
      try {
        ctx = JSON.parse(context);
      } catch {
        // ignore — fallback to name only
        ctx = { name: forName };
      }
      return api.post<Issued>("/v1/operations/certificates/issue", {
        template_code: code,
        student_id: studentId ? Number(studentId) : null,
        for_name: forName,
        context: ctx,
      });
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["operations-issued-certificates"] });
      setPreview(res.data);
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Issue failed.");
    },
  });

  return (
    <div className="space-y-6 print:space-y-2">
      <header className="print:hidden">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations · Certificates
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Issue certificate</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Pick a template, fill in the placeholders as JSON, issue. The rendered
          body is stored as an immutable snapshot with an auto-generated
          reference number.
        </p>
      </header>

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Fill in</CardTitle>
          <CardDescription>Placeholders are substituted {"{{like this}}"} on issue.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <Label>Template</Label>
            <select
              className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            >
              <option value="">—</option>
              {templates.filter((t) => t.is_active).map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>For (student's name)</Label>
            <Input value={forName} onChange={(e) => setForName(e.target.value)} />
          </div>
          <div>
            <Label>Student # (optional)</Label>
            <Input value={studentId} onChange={(e) => setStudentId(e.target.value)} />
          </div>
          <div className="col-span-3">
            <Label>Context (JSON, keys match {"{{placeholders}}"} in the template)</Label>
            <textarea
              className="mt-1 w-full rounded border border-input bg-transparent p-2 font-mono text-xs"
              rows={5}
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>
          {errorMsg && (
            <p className="col-span-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </p>
          )}
          <div className="col-span-3">
            <Button onClick={() => issue.mutate()} disabled={!code || !forName || issue.isPending}>
              <Send className="mr-1 h-4 w-4" /> Issue certificate
            </Button>
          </div>
        </CardContent>
      </Card>

      {preview && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 print:hidden">
            <div>
              <CardTitle>{preview.reference_no}</CardTitle>
              <CardDescription>Issued {preview.issued_on} · {preview.for_name}</CardDescription>
            </div>
            <Button onClick={() => window.print()}>
              <Printer className="mr-1 h-4 w-4" /> Print
            </Button>
          </CardHeader>
          <CardContent>
            <div
              className="rounded border border-input bg-white p-8 text-black"
              dangerouslySetInnerHTML={{ __html: preview.rendered_body }}
            />
          </CardContent>
        </Card>
      )}

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Recent certificates</CardTitle>
          <CardDescription>{issued.length} on record</CardDescription>
        </CardHeader>
        <CardContent>
          {issued.length === 0 ? (
            <p className="text-sm text-muted-foreground">None yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Ref</th>
                  <th>Template</th>
                  <th>For</th>
                  <th>Issued</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {issued.map((r) => (
                  <tr key={r.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-mono text-xs">{r.reference_no}</td>
                    <td>{r.template_code}</td>
                    <td>{r.for_name}</td>
                    <td>{r.issued_on}</td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setPreview(r)}
                      >
                        <FileText className="mr-1 h-3 w-3" /> View
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
