import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LibraryHeader } from "./_shared";
import { createShelf, deleteShelf, listShelves } from "./api";

/** Shelf / rack registry — now server-backed so every librarian sees the
 * same map. Reference a shelf code from a copy's notes to record where the
 * book physically lives. */
export function LibraryShelvesPage() {
  const qc = useQueryClient();
  const { data: shelves = [] } = useQuery({ queryKey: ["library-shelves"], queryFn: listShelves });

  const [code, setCode] = useState("");
  const [section, setSection] = useState("");
  const [capacity, setCapacity] = useState("40");

  const add = useMutation({
    mutationFn: () =>
      createShelf({
        code: code.trim(),
        section: section.trim() || undefined,
        capacity: Math.max(1, Number(capacity) || 40),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-shelves"] });
      setCode("");
      setSection("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteShelf(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-shelves"] }),
  });

  const canAdd = code.trim().length > 0 && !add.isPending;

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Shelves & racks"
        subtitle="Registry of every physical shelf. Reference the shelf code from a copy's notes to record where the book lives."
      />
      <Card>
        <CardHeader>
          <CardTitle>Add a shelf</CardTitle>
          <CardDescription>eg. Rack A, Shelf 3 → code "A-3"</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs uppercase tracking-wide text-muted-foreground">Code</label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="A-3" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-muted-foreground">Section</label>
            <Input value={section} onChange={(e) => setSection(e.target.value)} placeholder="Fiction" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-muted-foreground">Capacity</label>
            <Input
              type="number"
              min={1}
              value={capacity}
              onChange={(e) => setCapacity(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={() => add.mutate()} disabled={!canAdd}>
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Shelves ({shelves.length})</CardTitle>
          <CardDescription>Shared across the library team.</CardDescription>
        </CardHeader>
        <CardContent>
          {shelves.length === 0 ? (
            <p className="text-sm text-muted-foreground">No shelves yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2">Code</th>
                  <th>Section</th>
                  <th>Capacity</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {shelves.map((s) => (
                  <tr key={s.id} className="border-t border-saffron-pale">
                    <td className="py-2 font-mono text-indigo-dark">{s.code}</td>
                    <td>{s.section ?? "—"}</td>
                    <td>{s.capacity} books</td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => remove.mutate(s.id)}
                        disabled={remove.isPending}
                      >
                        <Trash2 className="mr-1 h-3 w-3" /> Remove
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
