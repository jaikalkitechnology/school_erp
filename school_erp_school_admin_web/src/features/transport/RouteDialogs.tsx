import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal, apiError } from "@/components/Modal";
import { deleteRoute, updateRoute, type Bus, type Driver, type Route } from "./api";

const select = "h-10 w-full rounded-md border border-input bg-background px-3 text-sm";

export function EditRouteDialog({
  route, buses, drivers, onClose, onSaved,
}: {
  route: Route;
  buses: Bus[];
  drivers: Driver[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [code, setCode] = useState(route.code);
  const [name, setName] = useState(route.name);
  const [busId, setBusId] = useState(route.bus_id ? String(route.bus_id) : "");
  const [driverId, setDriverId] = useState(route.driver_id ? String(route.driver_id) : "");
  const [active, setActive] = useState(route.is_active);
  const save = useMutation({
    mutationFn: () =>
      updateRoute(route.id, {
        code: code.trim(),
        name: name.trim(),
        bus_id: busId ? Number(busId) : null,
        driver_id: driverId ? Number(driverId) : null,
        is_active: active,
      }),
    onSuccess: () => {
      onSaved();
      onClose();
    },
  });
  return (
    <Modal title={`Edit route ${route.code}`} onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (code.trim() && name.trim()) save.mutate();
        }}
      >
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="edit-route-code">Code</Label>
            <Input id="edit-route-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="col-span-2 space-y-1.5">
            <Label htmlFor="edit-route-name">Name</Label>
            <Input id="edit-route-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="edit-route-bus">Bus</Label>
            <select id="edit-route-bus" className={select} value={busId} onChange={(e) => setBusId(e.target.value)}>
              <option value="">No bus</option>
              {buses.map((b) => (
                <option key={b.id} value={b.id}>{b.registration_number}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-route-driver">Driver</Label>
            <select id="edit-route-driver" className={select} value={driverId} onChange={(e) => setDriverId(e.target.value)}>
              <option value="">No driver</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>{d.full_name}</option>
              ))}
            </select>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-saffron" checked={active} onChange={(e) => setActive(e.target.checked)} />
          Active <span className="text-xs text-muted-foreground">(untick to stop running it but keep its trip history)</span>
        </label>
        {save.isError && <p className="text-sm text-destructive">{apiError(save.error, "Could not save the route.")}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={!code.trim() || !name.trim() || save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Confirm, then delete. If the backend refuses (students ride it, or it
 *  has trip history), its reason is shown instead of closing. */
export function DeleteRouteDialog({ route, onClose, onDeleted }: { route: Route; onClose: () => void; onDeleted: () => void }) {
  const del = useMutation({
    mutationFn: () => deleteRoute(route.id),
    onSuccess: () => {
      onDeleted();
      onClose();
    },
  });
  return (
    <Modal title={`Delete route ${route.code} · ${route.name}?`} onClose={onClose}>
      <p className="text-sm text-indigo-dark">
        Its {route.stop_count} stop{route.stop_count === 1 ? "" : "s"} are deleted too. A route students
        are assigned to, or one that has run trips, can't be deleted — mark it inactive instead.
      </p>
      {del.isError && (
        <p className="mt-3 flex gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {apiError(del.error, "Could not delete the route.")}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          {del.isError ? "Close" : "Cancel"}
        </Button>
        {!del.isError && (
          <Button type="button" variant="destructive" onClick={() => del.mutate()} disabled={del.isPending}>
            {del.isPending ? "Deleting…" : "Delete"}
          </Button>
        )}
      </div>
    </Modal>
  );
}
