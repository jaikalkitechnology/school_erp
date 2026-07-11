import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Settings } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { SimpleCrudPage, type FieldSpec } from "./_crud";

const ITEM_FIELDS: FieldSpec[] = [
  { key: "code", label: "Code", required: true },
  { key: "name", label: "Name", required: true },
  { key: "category", label: "Category", placeholder: "furniture / lab / sports" },
  { key: "unit", label: "Unit", placeholder: "pcs / kg / litre" },
  { key: "on_hand", label: "On hand", kind: "number" },
  { key: "reorder_level", label: "Reorder ≤", kind: "number" },
  { key: "unit_cost", label: "Unit cost ₹", kind: "number", hideInList: true },
  { key: "location", label: "Location", placeholder: "Store room A" },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

interface Item {
  id: number;
  code: string;
  name: string;
  on_hand: number;
  reorder_level: number;
  category: string | null;
  unit: string;
}

interface Movement {
  id: number;
  item_id: number;
  kind: "in" | "out" | "adjust";
  quantity: number;
  reference: string | null;
  occurred_on: string;
  notes: string | null;
}

export function InventoryItemsPage() {
  return (
    <SimpleCrudPage
      title="Inventory items"
      subtitle="Every non-library asset your school tracks — furniture, chemistry lab kit, sports equipment, IT hardware. Use Stock movements to add or remove quantity."
      endpoint="/v1/operations/inventory-items"
      queryKey="operations-inventory-items"
      fields={ITEM_FIELDS}
    />
  );
}

export function InventoryMovementsPage() {
  const qc = useQueryClient();
  const { data: items = [] } = useQuery({
    queryKey: ["operations-inventory-items"],
    queryFn: () => api.get<Item[]>("/v1/operations/inventory-items").then((r) => r.data),
  });
  const [itemId, setItemId] = useState<number | null>(null);
  const activeItem = items.find((i) => i.id === itemId);

  const [kind, setKind] = useState<"in" | "out" | "adjust">("in");
  const [qty, setQty] = useState("1");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

  const { data: movements = [] } = useQuery({
    queryKey: ["operations-inventory-movements", itemId],
    queryFn: () =>
      api
        .get<Movement[]>("/v1/operations/inventory-movements", {
          params: itemId ? { item_id: itemId } : undefined,
        })
        .then((r) => r.data),
  });

  const move = useMutation({
    mutationFn: () =>
      api.post("/v1/operations/inventory-movements", {
        item_id: itemId,
        kind,
        quantity: Number(qty),
        reference,
        occurred_on: new Date().toISOString().slice(0, 10),
        notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operations-inventory-items"] });
      qc.invalidateQueries({ queryKey: ["operations-inventory-movements"] });
      setQty("1");
      setReference("");
      setNotes("");
    },
  });

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations · Inventory
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Stock movements</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Log stock in (purchases, donations), stock out (issues, damage) and
          one-off adjustments. On-hand is updated in real time.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Items</CardTitle>
            <CardDescription>{items.length}</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[420px] space-y-1 overflow-y-auto p-3">
            {items.map((i) => (
              <button
                key={i.id}
                type="button"
                onClick={() => setItemId(i.id)}
                className={cn(
                  "flex w-full flex-col rounded-md border px-3 py-2 text-left transition-colors",
                  itemId === i.id
                    ? "border-saffron bg-saffron-pale text-saffron-darker"
                    : "border-transparent hover:bg-muted",
                  i.on_hand <= (i.reorder_level ?? 0) && "text-destructive",
                )}
              >
                <span className="text-sm font-semibold">{i.name}</span>
                <span className="text-xs text-muted-foreground">
                  {i.on_hand} {i.unit} on hand · {i.code}
                </span>
              </button>
            ))}
            {items.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No items yet. Add one on the Inventory items tab.
              </p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {!activeItem ? (
            <Card>
              <CardContent className="py-16 text-center text-sm text-muted-foreground">
                Pick an item on the left to see its movements.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>{activeItem.name}</CardTitle>
                  <CardDescription>
                    {activeItem.on_hand} {activeItem.unit} on hand
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  <div>
                    <Label>Kind</Label>
                    <select
                      className="mt-1 h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                      value={kind}
                      onChange={(e) => setKind(e.target.value as typeof kind)}
                    >
                      <option value="in">Stock in</option>
                      <option value="out">Stock out</option>
                      <option value="adjust">Adjust to</option>
                    </select>
                  </div>
                  <div>
                    <Label>Qty</Label>
                    <Input
                      type="number"
                      min={1}
                      value={qty}
                      onChange={(e) => setQty(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Reference</Label>
                    <Input value={reference} onChange={(e) => setReference(e.target.value)} />
                  </div>
                  <div>
                    <Label>Notes</Label>
                    <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
                  </div>
                  <div className="flex items-end">
                    <Button
                      onClick={() => move.mutate()}
                      disabled={move.isPending || !(Number(qty) > 0)}
                    >
                      Log
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Movement log</CardTitle>
                  <CardDescription>{movements.length} entries</CardDescription>
                </CardHeader>
                <CardContent>
                  {movements.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No movements yet.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <tr>
                          <th className="py-2">When</th>
                          <th>Kind</th>
                          <th>Qty</th>
                          <th>Ref</th>
                          <th>Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {movements.map((m) => (
                          <tr key={m.id} className="border-t border-saffron-pale">
                            <td className="py-2">{m.occurred_on}</td>
                            <td>
                              <span
                                className={cn(
                                  "inline-flex items-center rounded px-2 py-0.5 text-xs",
                                  m.kind === "in"
                                    ? "bg-teal-pale text-teal-dark"
                                    : m.kind === "out"
                                    ? "bg-destructive/15 text-destructive"
                                    : "bg-muted text-muted-foreground",
                                )}
                              >
                                {m.kind === "in" ? (
                                  <ArrowDown className="mr-1 h-3 w-3" />
                                ) : m.kind === "out" ? (
                                  <ArrowUp className="mr-1 h-3 w-3" />
                                ) : (
                                  <Settings className="mr-1 h-3 w-3" />
                                )}
                                {m.kind}
                              </span>
                            </td>
                            <td>{m.quantity}</td>
                            <td>{m.reference ?? "—"}</td>
                            <td>{m.notes ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
