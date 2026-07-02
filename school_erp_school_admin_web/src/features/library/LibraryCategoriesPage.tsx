import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deleteCategory, renameCategory, reports } from "./api";
import { LibraryHeader } from "./_shared";

/** Categories are free-text strings on Book.category — there's no
 * separate categories table. This page treats them as first-class
 * anyway:
 *
 *   * Read: distinct set from /library/reports.by_category
 *   * Create: happens implicitly when a book with a new category is
 *     saved on the Books tab
 *   * Update: rename endpoint bulk-updates every book carrying the
 *     old name
 *   * Delete: DELETE endpoint clears the category off every book
 *     that carries it (books survive, they just become
 *     "Uncategorised")
 */
export function LibraryCategoriesPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["library-reports"],
    queryFn: reports,
  });

  const [renaming, setRenaming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const del = useMutation({
    mutationFn: (name: string) => deleteCategory(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-reports"] });
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
        typeof detail === "string" ? detail : "Could not delete category.",
      );
    },
  });

  const namedCategories = (data?.by_category ?? []).filter(
    (c): c is { category: string; books: number; copies: number } =>
      c.category !== null,
  );

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Categories"
        subtitle="Every category currently in use. Add one by saving a book with a new category name; rename or delete propagates to every book that carries it."
      />
      <Card>
        <CardHeader>
          <CardTitle>Category list</CardTitle>
          <CardDescription>
            {data
              ? `${namedCategories.length} named${
                  data.by_category.some((c) => c.category === null)
                    ? " · Uncategorised bucket present"
                    : ""
                }`
              : "Loading…"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !data || data.by_category.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No categories yet. Add one when you save a book on the Books tab.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Category</th>
                  <th>Books</th>
                  <th>Copies</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.by_category.map((c, i) => {
                  const name = c.category;
                  const isNamed = name !== null;
                  return (
                    <tr key={i} className="border-t border-saffron-pale">
                      <td className="py-2 font-medium text-indigo-dark">
                        {name ?? (
                          <span className="italic text-muted-foreground">
                            Uncategorised
                          </span>
                        )}
                      </td>
                      <td>{c.books}</td>
                      <td>{c.copies}</td>
                      <td className="text-right">
                        {isNamed && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setRenaming(name)}
                            >
                              <Pencil className="mr-1 h-3 w-3" />
                              Rename
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
                              <Trash2 className="mr-1 h-3 w-3" />
                              Delete
                            </Button>
                          </>
                        )}
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
        <RenameCategoryDialog
          from={renaming}
          onClose={() => setRenaming(null)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["library-reports"] });
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
            The category is cleared off every book that currently carries it.
            Books survive — they become "Uncategorised" and you can re-tag
            them from the Books tab.
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
              Delete category
            </Button>
          </div>
        </ModalShell>
      )}
    </div>
  );
}

function RenameCategoryDialog({
  from,
  onClose,
  onSaved,
}: {
  from: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [to, setTo] = useState(from);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const rename = useMutation({
    mutationFn: () => renameCategory(from, to.trim()),
    onSuccess: onSaved,
    onError: (err: unknown) => {
      const detail =
        typeof err === "object" && err !== null && "response" in err
          ? // @ts-expect-error - axios error shape
            err.response?.data?.detail
          : undefined;
      setErrorMsg(
        typeof detail === "string" ? detail : "Could not rename category.",
      );
    },
  });
  return (
    <ModalShell title={`Rename "${from}"`} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <Label>New name</Label>
          <Input value={to} onChange={(e) => setTo(e.target.value)} />
          <p className="mt-1 text-xs text-muted-foreground">
            Every book currently tagged "{from}" is retagged. Nothing else
            changes.
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
            onClick={() => {
              setErrorMsg(null);
              rename.mutate();
            }}
            disabled={!to.trim() || to.trim() === from || rename.isPending}
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
