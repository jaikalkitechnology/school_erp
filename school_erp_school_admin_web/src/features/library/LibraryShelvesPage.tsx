import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LibraryHeader } from "./_shared";

interface Shelf {
  id: string;
  code: string;   // eg. A-3
  section: string;// eg. Fiction
  capacity: number;
}

const STORE_KEY = "jaikalki.library.shelves.v1";

/** Shelf / rack registry. Shelves are a client-side concept until
 * we add a proper table — the librarian can name racks (A, B, C…)
 * and shelves within them, and use the codes in a copy's notes
 * field to record where a given book lives on the floor. */
export function LibraryShelvesPage() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [code, setCode] = useState("");
  const [section, setSection] = useState("");
  const [capacity, setCapacity] = useState("40");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) setShelves(JSON.parse(raw) as Shelf[]);
    } catch {
      // ignore corrupt storage
    }
  }, []);

  const persist = (rows: Shelf[]) => {
    setShelves(rows);
    localStorage.setItem(STORE_KEY, JSON.stringify(rows));
  };

  const add = () => {
    if (!code.trim() || !section.trim()) return;
    persist([
      ...shelves,
      {
        id: `${Date.now()}`,
        code: code.trim(),
        section: section.trim(),
        capacity: Math.max(1, Number(capacity) || 40),
      },
    ]);
    setCode("");
    setSection("");
  };

  const remove = (id: string) => persist(shelves.filter((s) => s.id !== id));

  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Shelves & racks"
        subtitle="Registry of every physical shelf in the library. Reference the shelf code from a copy's notes to record where the book lives."
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
            <Input
              value={section}
              onChange={(e) => setSection(e.target.value)}
              placeholder="Fiction"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-muted-foreground">Capacity</label>
            <Input type="number" min={1} value={capacity} onChange={(e) => setCapacity(e.target.value.replace(/\D/g, ""))} />
          </div>
          <div className="flex items-end">
            <Button onClick={add} disabled={!code.trim() || !section.trim()}>
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Shelves ({shelves.length})</CardTitle>
          <CardDescription>
            Stored locally in your browser for now — a dedicated shelves table
            will move this to the server so every librarian sees the same map.
          </CardDescription>
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
                    <td>{s.section}</td>
                    <td>{s.capacity} books</td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => remove(s.id)}
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
