import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LibraryHeader } from "./_shared";

/** Shared component powering Authors + Publishers. They both live
 * as free-text strings on Book.author / Book.publisher — the CRUD
 * shape mirrors Categories: list, rename (bulk update), delete
 * (bulk null-out).
 *
 * The row type is generic; the caller passes small accessor
 * callbacks (nameOf / countOf) so we don't need a structural
 * constraint on T. */
export function NameListPage<T>({
  title,
  subtitle,
  queryKey,
  singular,
  fetchList,
  nameOf,
  countOf,
  renameOne,
  deleteOne,
}: {
  title: string;
  subtitle: string;
  queryKey: string;
  singular: string;
  fetchList: () => Promise<T[]>;
  nameOf: (row: T) => string;
  countOf: (row: T) => number;
  renameOne: (from: string, to: string) => Promise<unknown>;
  deleteOne: (name: string) => Promise<unknown>;
}) {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const { data = [], isLoading } = useQuery({
    queryKey: [queryKey],
    queryFn: fetchList,
  });

  const [renaming, setRenaming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const del = useMutation({
    mutationFn: (name: string) => deleteOne(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [queryKey] });
      qc.invalidateQueries({ queryKey: ["library-books"] });
      setDeleting(null);
      setErrorMsg(null);
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(
        typeof detail === "string"
          ? detail
          : `Could not delete ${singular.toLowerCase()}.`,
      );
    },
  });

  const filtered = data.filter((row) => {
    const name = nameOf(row);
    if (!q.trim()) return true;
    return name.toLowerCase().includes(q.trim().toLowerCase());
  });

  return (
    <div className="space-y-6">
      <LibraryHeader title={title} subtitle={subtitle} />
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>{title} in use</CardTitle>
            <CardDescription>
              {isLoading ? "Loading…" : `${data.length} distinct`}
            </CardDescription>
          </div>
          <div className="w-64">
            <Input
              placeholder={`Filter ${title.toLowerCase()}`}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : data.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              None yet. Add one by saving a book with a new{" "}
              {singular.toLowerCase()} on the Books tab.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">{singular}</th>
                  <th>Books</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, i) => {
                  const name = nameOf(row);
                  return (
                    <tr key={i} className="border-t border-saffron-pale">
                      <td className="py-2 font-medium text-indigo-dark">
                        {name}
                      </td>
                      <td>{countOf(row)}</td>
                      <td className="text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setRenaming(name)}
                        >
                          <Pencil className="mr-1 h-3 w-3" /> Rename
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setDeleting(name);
                            setErrorMsg(null);
                          }}
                        >
                          <Trash2 className="mr-1 h-3 w-3" /> Delete
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {renaming !== null && (
        <RenameDialog
          singular={singular}
          from={renaming}
          onClose={() => setRenaming(null)}
          onSave={async (to) => {
            await renameOne(renaming, to);
            qc.invalidateQueries({ queryKey: [queryKey] });
            qc.invalidateQueries({ queryKey: ["library-books"] });
            setRenaming(null);
          }}
        />
      )}

      {deleting !== null && (
        <ModalShell
          title={`Delete "${deleting}"?`}
          onClose={() => {
            setDeleting(null);
            setErrorMsg(null);
          }}
        >
          <p className="text-sm text-muted-foreground">
            The {singular.toLowerCase()} is cleared off every book that
            carries it. Books survive.
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
                setDeleting(null);
                setErrorMsg(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => del.mutate(deleting)}
              disabled={del.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete {singular.toLowerCase()}
            </Button>
          </div>
        </ModalShell>
      )}
    </div>
  );
}

function RenameDialog({
  singular,
  from,
  onClose,
  onSave,
}: {
  singular: string;
  from: string;
  onClose: () => void;
  onSave: (to: string) => Promise<void>;
}) {
  const [to, setTo] = useState(from);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErrorMsg(null);
    setBusy(true);
    try {
      await onSave(to.trim());
    } catch (err: unknown) {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(
        typeof detail === "string"
          ? detail
          : `Could not rename ${singular.toLowerCase()}.`,
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalShell title={`Rename "${from}"`} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <Label>New name</Label>
          <Input value={to} onChange={(e) => setTo(e.target.value)} />
          <p className="mt-1 text-xs text-muted-foreground">
            Every book tagged "{from}" is retagged to the new name.
          </p>
        </div>
        {errorMsg && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {errorMsg}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={!to.trim() || to.trim() === from || busy}
          >
            Rename
          </Button>
        </div>
      </div>
    </ModalShell>
  );
}

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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg border border-saffron-pale bg-warm-white p-6 shadow-lg">
        <div className="mb-4 flex items-start justify-between">
          <h2 className="font-display text-xl text-indigo-dark">{title}</h2>
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
