import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  deleteHostel,
  deleteRoom,
  updateHostel,
  updateRoom,
  type Hostel,
  type HostelKind,
  type Room,
  type RoomStatus,
} from "./api";

/** Message from an API error (the backend explains refusals in `detail`). */
export function apiError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" && detail !== "Validation error" ? detail : fallback;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div role="dialog" aria-label={title} className="w-full max-w-md rounded-t-lg bg-warm-white p-5 shadow-lg sm:rounded-lg">
        <div className="mb-4 flex items-start justify-between">
          <h2 className="font-display text-lg text-indigo-dark">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted-foreground hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const select = "h-10 w-full rounded-md border border-input bg-background px-3 text-sm";

export function EditHostelDialog({ hostel, onClose, onSaved }: { hostel: Hostel; onClose: () => void; onSaved: () => void }) {
  const [code, setCode] = useState(hostel.code);
  const [name, setName] = useState(hostel.name);
  const [kind, setKind] = useState<HostelKind>(hostel.kind);
  const [active, setActive] = useState(hostel.is_active);
  const save = useMutation({
    mutationFn: () =>
      updateHostel(hostel.id, {
        code: code.trim(),
        name: name.trim(),
        kind,
        is_active: active,
        warden_user_id: hostel.warden_user_id,
        address: hostel.address,
      }),
    onSuccess: () => {
      onSaved();
      onClose();
    },
  });
  return (
    <Modal title={`Edit ${hostel.name}`} onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (code.trim() && name.trim()) save.mutate();
        }}
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="edit-hostel-code">Code</Label>
            <Input id="edit-hostel-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-hostel-kind">For</Label>
            <select id="edit-hostel-kind" className={select} value={kind} onChange={(e) => setKind(e.target.value as HostelKind)}>
              <option value="boys">Boys</option>
              <option value="girls">Girls</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="edit-hostel-name">Name</Label>
          <Input id="edit-hostel-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-saffron" checked={active} onChange={(e) => setActive(e.target.checked)} />
          Active <span className="text-xs text-muted-foreground">(untick to stop using it without deleting records)</span>
        </label>
        {save.isError && <p className="text-sm text-destructive">{apiError(save.error, "Could not save the hostel.")}</p>}
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

export function EditRoomDialog({ room, onClose, onSaved }: { room: Room; onClose: () => void; onSaved: () => void }) {
  const [number, setNumber] = useState(room.number);
  const [floor, setFloor] = useState(room.floor ?? "");
  const [capacity, setCapacity] = useState(String(room.capacity));
  const [fee, setFee] = useState(String(room.monthly_fee));
  const [roomStatus, setRoomStatus] = useState<RoomStatus>(room.status);
  const cap = Number(capacity);
  const capError = !Number.isInteger(cap) || cap < 1
    ? "Capacity must be 1 or more."
    : cap < room.occupied
      ? `${room.occupied} students live here, so capacity can't be below ${room.occupied}.`
      : null;
  const save = useMutation({
    mutationFn: () =>
      updateRoom(room.id, {
        number: number.trim(),
        floor: floor.trim() || null,
        capacity: cap,
        monthly_fee: Number(fee) || 0,
        status: roomStatus,
      }),
    onSuccess: () => {
      onSaved();
      onClose();
    },
  });
  return (
    <Modal title={`Edit room ${room.number}`} onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (number.trim() && !capError) save.mutate();
        }}
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="edit-room-number">Number</Label>
            <Input id="edit-room-number" value={number} onChange={(e) => setNumber(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-room-floor">Floor</Label>
            <Input id="edit-room-floor" value={floor} placeholder="eg. 1" onChange={(e) => setFloor(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-room-capacity">Capacity</Label>
            <Input
              id="edit-room-capacity"
              inputMode="numeric"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value.replace(/\D/g, ""))}
              className={capError ? "border-destructive" : undefined}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-room-fee">Monthly fee (₹)</Label>
            <Input id="edit-room-fee" inputMode="decimal" value={fee} onChange={(e) => setFee(e.target.value.replace(/[^\d.]/g, ""))} />
          </div>
        </div>
        {capError && <p className="text-xs text-destructive">{capError}</p>}
        <div className="space-y-1.5">
          <Label htmlFor="edit-room-status">Status</Label>
          <select id="edit-room-status" className={select} value={roomStatus} onChange={(e) => setRoomStatus(e.target.value as RoomStatus)}>
            <option value="available">Available</option>
            <option value="full">Full</option>
            <option value="under_maintenance">Under maintenance</option>
          </select>
        </div>
        {save.isError && <p className="text-sm text-destructive">{apiError(save.error, "Could not save the room.")}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={!number.trim() || !!capError || save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Confirm, then delete. If the backend refuses (records would be lost),
 *  its reason is shown instead of closing. */
export function DeleteDialog({
  what,
  onClose,
  onDeleted,
}: {
  what: { kind: "hostel"; item: Hostel } | { kind: "room"; item: Room };
  onClose: () => void;
  onDeleted: () => void;
}) {
  const label = what.kind === "hostel" ? what.item.name : `room ${what.item.number}`;
  const del = useMutation({
    mutationFn: () => (what.kind === "hostel" ? deleteHostel(what.item.id) : deleteRoom(what.item.id)),
    onSuccess: () => {
      onDeleted();
      onClose();
    },
  });
  return (
    <Modal title={`Delete ${label}?`} onClose={onClose}>
      <p className="text-sm text-indigo-dark">
        {what.kind === "hostel"
          ? "Its rooms and mess menus are deleted too. A hostel with student records can't be deleted — mark it inactive instead."
          : "Only a room nobody has lived in can be deleted."}
      </p>
      {del.isError && (
        <p className="mt-3 flex gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {apiError(del.error, "Could not delete.")}
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
