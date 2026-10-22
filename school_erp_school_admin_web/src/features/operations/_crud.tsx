import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/datetime";
import { api } from "@/lib/api";

// ---- Types ---------------------------------------------------------------

export type FieldKind =
  | "text"
  | "number"
  | "date"
  | "datetime"
  | "textarea"
  | "select"
  | "checkbox"
  | "picker"
  | "phone"
  | "email"
  | "gst"
  /** A JSON value (eg. a list of ids) drawn by the field's renderInput. */
  | "json";

export interface PickerOption {
  id: number;
  label: string;
  hint?: string;
}

export interface FieldSpec {
  key: string;
  label: string;
  kind?: FieldKind;
  options?: { value: string; label: string }[];
  /** For kind="picker": function that returns the option list. Called
   *  once when the form opens; results are cached in-component. */
  fetchOptions?: () => Promise<PickerOption[]>;
  required?: boolean;
  hideInList?: boolean;
  hideInForm?: boolean;
  placeholder?: string;
  render?: (row: Record<string, unknown>) => React.ReactNode;
  /** Draw the form input yourself. `values` are the other fields' current
   *  (string) values, eg. to depend on what's picked in a select. */
  renderInput?: (p: {
    value: string;
    values: Record<string, string>;
    onChange: (v: string) => void;
    invalid: boolean;
  }) => React.ReactNode;
  /** Clear these fields whenever this one changes. */
  resets?: string[];
  /** Extra check on submit; return a message to block saving. */
  validate?: (raw: string, values: Record<string, string>) => string | null;
}

export interface CrudProps {
  title: string;
  subtitle?: string;
  endpoint: string;              // e.g. "/v1/operations/admissions"
  queryKey: string;              // e.g. "operations-admissions"
  fields: FieldSpec[];
  primaryLabel?: (row: Record<string, unknown>) => string;
  extraTop?: React.ReactNode;    // eg. a stats row
  extraActions?: (row: Record<string, unknown>) => React.ReactNode; // per-row extra buttons
  emptyMessage?: string;
}

// ---- API glue ------------------------------------------------------------

const list = (endpoint: string) =>
  api.get<Record<string, unknown>[]>(endpoint).then((r) => r.data);
const create = (endpoint: string, body: Record<string, unknown>) =>
  api.post<Record<string, unknown>>(endpoint, body).then((r) => r.data);
const patch = (endpoint: string, id: number, body: Record<string, unknown>) =>
  api.patch<Record<string, unknown>>(`${endpoint}/${id}`, body).then((r) => r.data);
const del = (endpoint: string, id: number) =>
  api.delete(`${endpoint}/${id}`).then((r) => r.data);

// ---- Utility -------------------------------------------------------------

const toInputValue = (v: unknown, kind?: FieldKind): string => {
  if (v === null || v === undefined) return "";
  if (kind === "date" && typeof v === "string") return v.slice(0, 10);
  if (kind === "datetime" && typeof v === "string") return v.slice(0, 16);
  if (kind === "checkbox") return v ? "true" : "false";
  if (kind === "json") return JSON.stringify(v);
  return String(v);
};

const fromInputValue = (v: string, kind?: FieldKind): unknown => {
  if (kind === "number" || kind === "picker") return v === "" ? null : Number(v);
  if (kind === "checkbox") return v === "true";
  if (kind === "date" || kind === "datetime") return v || null;
  if (kind === "json") {
    if (v === "") return null;
    const parsed = JSON.parse(v);
    return Array.isArray(parsed) && parsed.length === 0 ? null : parsed;
  }
  return v === "" ? null : v;
};

// ---- Table ---------------------------------------------------------------

export function SimpleCrudPage({
  title,
  subtitle,
  endpoint,
  queryKey,
  fields,
  primaryLabel,
  extraTop,
  extraActions,
  emptyMessage,
}: CrudProps) {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: [queryKey],
    queryFn: () => list(endpoint),
  });

  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Record<string, unknown> | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const delMut = useMutation({
    mutationFn: (id: number) => del(endpoint, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [queryKey] });
      setConfirmDelete(null);
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(typeof detail === "string" ? detail : "Delete failed.");
    },
  });

  const listFields = useMemo(
    () => fields.filter((f) => !f.hideInList),
    [fields],
  );

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations
        </p>
        <div className="mt-1 flex items-center justify-between">
          <h1 className="font-display text-4xl text-indigo-dark">{title}</h1>
          <Button onClick={() => setCreating(true)}>
            <Plus className="mr-1 h-4 w-4" /> Add
          </Button>
        </div>
        {subtitle && (
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            {subtitle}
          </p>
        )}
      </header>

      {extraTop}

      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {isLoading ? "Loading…" : `${data.length} rows`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : data.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {emptyMessage ?? "No rows yet. Click Add to create one."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-max text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    {listFields.map((f) => (
                      <th key={f.key} className="py-2 pr-4">
                        {f.label}
                      </th>
                    ))}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row) => (
                    <tr
                      key={String(row.id)}
                      className="border-t border-saffron-pale"
                    >
                      {listFields.map((f, i) => (
                        <td key={f.key} className="py-2 pr-4">
                          {f.render
                            ? f.render(row)
                            : renderCell(row[f.key], f.kind)}
                          {i === 0 && primaryLabel && (
                            <span className="ml-1 text-[10px] text-muted-foreground">
                              #{String(row.id)}
                            </span>
                          )}
                        </td>
                      ))}
                      <td className="text-right">
                        {extraActions && extraActions(row)}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditing(row)}
                        >
                          <Pencil className="mr-1 h-3 w-3" /> Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setConfirmDelete(row);
                            setErrorMsg(null);
                          }}
                        >
                          <Trash2 className="mr-1 h-3 w-3" /> Delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {creating && (
        <FormDialog
          title={`Add ${title.replace(/s$/, "").toLowerCase()}`}
          fields={fields}
          initial={{}}
          onClose={() => setCreating(false)}
          onSave={async (body) => {
            await create(endpoint, body);
            qc.invalidateQueries({ queryKey: [queryKey] });
            setCreating(false);
          }}
        />
      )}
      {editing && (
        <FormDialog
          title={`Edit`}
          fields={fields}
          initial={editing}
          onClose={() => setEditing(null)}
          onSave={async (body) => {
            await patch(endpoint, Number(editing.id), body);
            qc.invalidateQueries({ queryKey: [queryKey] });
            setEditing(null);
          }}
        />
      )}
      {confirmDelete && (
        <ModalShell
          title={`Delete row #${confirmDelete.id}?`}
          onClose={() => {
            setConfirmDelete(null);
            setErrorMsg(null);
          }}
        >
          <p className="text-sm text-muted-foreground">
            This can't be undone.
          </p>
          {errorMsg && (
            <p className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </p>
          )}
          <div className="mt-4 flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmDelete(null);
                setErrorMsg(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => delMut.mutate(Number(confirmDelete.id))}
              disabled={delMut.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </Button>
          </div>
        </ModalShell>
      )}
    </div>
  );
}

function renderCell(v: unknown, kind?: FieldKind): React.ReactNode {
  if (v === null || v === undefined || v === "") return <span className="text-muted-foreground">—</span>;
  if (kind === "checkbox") return v ? "Yes" : "No";
  if (kind === "date" && typeof v === "string") return v.slice(0, 10);
  // Typed into a date-time box, so shown as entered (no zone shift).
  if (kind === "datetime" && typeof v === "string") return formatDateTime(v, "wall");
  if (typeof v === "object") return <span className="font-mono text-xs">{JSON.stringify(v)}</span>;
  return String(v);
}

// ---- Form dialog ---------------------------------------------------------

function FormDialog({
  title,
  fields,
  initial,
  onClose,
  onSave,
}: {
  title: string;
  fields: FieldSpec[];
  initial: Record<string, unknown>;
  onClose: () => void;
  onSave: (body: Record<string, unknown>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const out: Record<string, string> = {};
    for (const f of fields) {
      out[f.key] = toInputValue(initial[f.key], f.kind);
    }
    return out;
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const formFields = fields.filter((f) => !f.hideInForm);

  /** Client-side validation before we POST. Returns a map of
   * field-key → message; empty means valid. Catches the common cases
   * so the user gets an inline red hint instead of a round-trip 400:
   *   - required field left blank
   *   - number field with a negative value (all our numeric fields
   *     are counts / money / marks, none of which go below zero)
   *   - number field that isn't actually a number */
  const validate = (): Record<string, string> => {
    const errs: Record<string, string> = {};
    for (const f of formFields) {
      const raw = (values[f.key] ?? "").trim();
      if (f.required && raw === "") {
        errs[f.key] = "Required";
        continue;
      }
      const custom = f.validate?.(raw, values);
      if (custom) {
        errs[f.key] = custom;
        continue;
      }
      if (raw !== "" && f.kind === "number") {
        const n = Number(raw);
        if (Number.isNaN(n)) errs[f.key] = "Must be a number";
        else if (n < 0) errs[f.key] = "Cannot be negative";
      }
      if (raw !== "" && f.kind === "phone") {
        // Exactly 10 digits (Indian mobile). Strip anything else out
        // first so a pasted "+91 98765 43210" is judged on its digits.
        const digits = raw.replace(/\D/g, "");
        if (digits.length !== 10) {
          errs[f.key] = "Enter a 10-digit phone number";
        }
      }
      if (raw !== "" && f.kind === "email") {
        // Strict: local + domain may only contain letters, digits,
        // dots and hyphens — this rejects ~!#$%^&*()_+|?><":{},;' and
        // spaces. A single @ and a 2+ letter TLD are required.
        if (!/^[a-zA-Z0-9.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(raw)) {
          errs[f.key] = "Only letters, digits, . and - allowed — no special symbols";
        }
      }
      if (raw !== "" && f.kind === "gst") {
        // Indian GSTIN is exactly 15 alphanumeric characters.
        if (!/^[0-9A-Z]{15}$/.test(raw)) {
          errs[f.key] = "GST must be 15 letters/digits";
        }
      }
    }
    return errs;
  };

  const submit = async () => {
    setErrorMsg(null);
    const errs = validate();
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) {
      setErrorMsg("Please fix the highlighted fields.");
      return;
    }
    setBusy(true);
    try {
      const body: Record<string, unknown> = {};
      for (const f of formFields) {
        body[f.key] = fromInputValue(values[f.key] ?? "", f.kind);
      }
      await onSave(body);
    } catch (err: unknown) {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      const field =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.field
          : undefined;
      // If the backend named a field (operations _FieldError), pin the
      // message to that input too.
      if (typeof field === "string") {
        setFieldErrors((prev) => ({
          ...prev,
          [field]: typeof detail === "string" ? detail.replace(`${field}: `, "") : "Invalid",
        }));
      }
      setErrorMsg(typeof detail === "string" ? detail : "Save failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalShell title={title} onClose={onClose}>
      <div className="grid max-h-[70vh] grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
        {formFields.map((f) => (
          <div
            key={f.key}
            className={cn(
              f.kind === "textarea" || f.renderInput ? "col-span-2" : "",
            )}
          >
            <Label>
              {f.label}
              {f.required && <span className="text-destructive"> *</span>}
            </Label>
            {f.renderInput ? (
              f.renderInput({
                value: values[f.key] ?? "",
                values,
                invalid: Boolean(fieldErrors[f.key]),
                onChange: (v) => {
                  setValues((prev) => ({ ...prev, [f.key]: v }));
                  setErrorMsg(null);
                  setFieldErrors((prev) => {
                    const next = { ...prev };
                    delete next[f.key];
                    return next;
                  });
                },
              })
            ) : f.kind === "textarea" ? (
              <textarea
                className="mt-1 w-full rounded border border-input bg-transparent p-2 text-sm"
                rows={3}
                value={values[f.key] ?? ""}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
              />
            ) : f.kind === "select" ? (
              <select
                className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={values[f.key] ?? ""}
                onChange={(e) => {
                  const next = { ...values, [f.key]: e.target.value };
                  for (const r of f.resets ?? []) next[r] = "";
                  setValues(next);
                }}
              >
                <option value="">—</option>
                {(f.options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            ) : f.kind === "checkbox" ? (
              <label className="mt-2 flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={values[f.key] === "true"}
                  onChange={(e) =>
                    setValues({ ...values, [f.key]: e.target.checked ? "true" : "false" })
                  }
                />
                Enabled
              </label>
            ) : f.kind === "picker" ? (
              <PickerField
                field={f}
                value={values[f.key] ?? ""}
                onChange={(v) => setValues({ ...values, [f.key]: v })}
              />
            ) : (
              <Input
                type={
                  f.kind === "number" ? "number"
                    : f.kind === "date" ? "date"
                    : f.kind === "datetime" ? "datetime-local"
                    : f.kind === "email" ? "email"
                    : f.kind === "phone" ? "tel"
                    : "text"
                }
                min={f.kind === "number" ? 0 : undefined}
                inputMode={f.kind === "phone" ? "numeric" : undefined}
                maxLength={
                  f.kind === "phone" ? 10 : f.kind === "gst" ? 15 : undefined
                }
                value={values[f.key] ?? ""}
                onChange={(e) => {
                  let v = e.target.value;
                  // Phone: digits only, capped at 10.
                  if (f.kind === "phone") {
                    v = v.replace(/\D/g, "").slice(0, 10);
                  }
                  // GST: uppercase alphanumeric only, capped at 15.
                  else if (f.kind === "gst") {
                    v = v.toUpperCase().replace(/[^0-9A-Z]/g, "").slice(0, 15);
                  }
                  // Email: strip the special symbols the user can't use
                  // (keep letters, digits, @ . _ - + so typing feels
                  // natural; the submit check enforces the final shape).
                  else if (f.kind === "email") {
                    v = v.replace(/[~!#$%^&*()|?><":{},;'\s]/g, "");
                  }
                  setValues({ ...values, [f.key]: v });
                  if (fieldErrors[f.key]) {
                    setFieldErrors((prev) => {
                      const next = { ...prev };
                      delete next[f.key];
                      return next;
                    });
                  }
                }}
                placeholder={
                  f.placeholder ??
                  (f.kind === "phone"
                    ? "10-digit mobile"
                    : f.kind === "gst"
                    ? "15-character GSTIN"
                    : undefined)
                }
                className={cn(fieldErrors[f.key] && "border-destructive")}
              />
            )}
            {fieldErrors[f.key] && (
              <p className="mt-1 text-xs text-destructive">{fieldErrors[f.key]}</p>
            )}
          </div>
        ))}
      </div>
      {errorMsg && (
        <p className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errorMsg}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={submit} disabled={busy}>
          Save
        </Button>
      </div>
    </ModalShell>
  );
}

// ---- Modal shell ---------------------------------------------------------

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div className="max-h-[95vh] w-full max-w-3xl overflow-y-auto rounded-t-lg border-t border-saffron-pale bg-warm-white p-4 shadow-lg sm:rounded-lg sm:border sm:p-6">
        <div className="mb-4 flex items-start justify-between">
          <h2 className="font-display text-lg text-indigo-dark sm:text-xl">
            {title}
          </h2>
          <button
            type="button"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ---- Picker field: fetches options from the server -------------------
// Prevents users from typing an FK value that doesn't exist. Renders a
// searchable dropdown with a "None" option so nullable FKs stay
// nullable.

function PickerField({
  field,
  value,
  onChange,
}: {
  field: FieldSpec;
  value: string;
  onChange: (v: string) => void;
}) {
  const { data: options = [], isLoading } = useQuery({
    queryKey: ["crud-picker", field.key],
    queryFn: () => field.fetchOptions?.() ?? Promise.resolve([]),
  });
  const selected = options.find((o) => String(o.id) === String(value));
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = options.filter((o) => {
    if (!q.trim()) return true;
    const needle = q.trim().toLowerCase();
    return (
      o.label.toLowerCase().includes(needle) ||
      String(o.id) === needle ||
      (o.hint ?? "").toLowerCase().includes(needle)
    );
  });

  if (isLoading) {
    return (
      <p className="mt-1 text-xs text-muted-foreground">Loading options…</p>
    );
  }

  return (
    <div className="relative">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setOpen((o) => !o);
        }}
        className={cn(
          "mt-1 flex h-9 w-full cursor-pointer items-center rounded border border-input bg-transparent px-3 text-sm",
          open && "border-saffron",
        )}
      >
        {selected ? (
          <span>
            <span className="font-medium">{selected.label}</span>
            <span className="ml-1 text-xs text-muted-foreground">
              #{selected.id}
              {selected.hint ? ` · ${selected.hint}` : ""}
            </span>
          </span>
        ) : value ? (
          <span className="text-destructive">
            Unknown #{value} (clear or pick another)
          </span>
        ) : (
          <span className="text-muted-foreground">
            {field.placeholder ?? `Pick ${field.label.toLowerCase()}`}
          </span>
        )}
        <span className="ml-auto text-muted-foreground">▾</span>
      </div>
      {open && (
        <div className="absolute left-0 right-0 top-11 z-30 max-h-64 overflow-y-auto rounded-md border border-input bg-warm-white shadow-lg">
          <div className="border-b border-input p-2">
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search…"
              autoFocus
            />
          </div>
          <button
            type="button"
            onClick={() => {
              onChange("");
              setOpen(false);
              setQ("");
            }}
            className="flex w-full items-center gap-2 border-b border-saffron-pale px-3 py-2 text-left text-sm text-muted-foreground hover:bg-muted"
          >
            <span className="italic">None</span>
          </button>
          {filtered.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              No matches. If the row you want doesn't exist yet, add it
              first on its own page.
            </p>
          ) : (
            filtered.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => {
                  onChange(String(o.id));
                  setOpen(false);
                  setQ("");
                }}
                className={cn(
                  "flex w-full items-center gap-2 border-t border-saffron-pale/50 px-3 py-2 text-left text-sm first:border-t-0 hover:bg-saffron-pale/60",
                  String(o.id) === String(value) && "bg-saffron-pale",
                )}
              >
                <div className="flex-1">
                  <p className="font-medium">{o.label}</p>
                  {o.hint && (
                    <p className="text-xs text-muted-foreground">{o.hint}</p>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">#{o.id}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export { ModalShell };
