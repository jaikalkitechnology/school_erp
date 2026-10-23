import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building, ChefHat, ClipboardList, DoorOpen, FileWarning, Pencil, Plus, Trash2, UserCheck, UserMinus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StudentPicker } from "@/components/StudentPicker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  addDisciplinary,
  applyLeave,
  checkInVisitor,
  checkOutVisitor,
  createHostel,
  createRoom,
  decideLeave,
  listDisciplinary,
  listHostels,
  listLeaves,
  listMess,
  listRooms,
  listVisitors,
  markReturned,
  reports,
  upsertAllocation,
  upsertMess,
  type DisciplinarySeverity,
  type HostelKind,
  type HostelLeaveStatus,
  type MealType,
  type Hostel,
  type Room,
} from "./api";
import { apiError } from "@/components/Modal";
import { DeleteDialog, EditHostelDialog, EditRoomDialog } from "./SetupDialogs";

const TABS = ["Setup", "Allocations", "Mess", "Visitors", "Discipline", "Leaves", "Reports"] as const;
type Tab = (typeof TABS)[number];

const LEAVE_TONE: Record<HostelLeaveStatus, string> = {
  pending: "bg-marigold-pale text-marigold-dark",
  approved: "bg-teal-pale text-teal-dark",
  rejected: "bg-destructive/15 text-destructive",
  returned: "bg-muted text-muted-foreground",
};

const SEVERITY_TONE: Record<DisciplinarySeverity, string> = {
  note: "bg-muted text-muted-foreground",
  warning: "bg-marigold-pale text-marigold-dark",
  suspension: "bg-destructive/15 text-destructive",
};

export function HostelPage() {
  const [tab, setTab] = useState<Tab>("Setup");
  const [hostelId, setHostelId] = useState<number | null>(null);

  const { data: hostels = [] } = useQuery({ queryKey: ["hostels"], queryFn: listHostels });

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 19 · Hostel
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Hostel</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Optional per school. Manage hostels, rooms, allocations, mess, visitor logs,
          discipline, and overnight leaves.
        </p>
      </header>

      <Card>
        <CardContent className="flex items-center gap-3 py-3">
          <Label className="m-0">Active hostel</Label>
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={hostelId ?? ""}
            onChange={(e) => setHostelId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Select…</option>
            {hostels.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name} ({h.kind})
              </option>
            ))}
          </select>
        </CardContent>
      </Card>

      <nav className="flex flex-wrap gap-1 border-b border-saffron-pale">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setTab(label)}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === label
                ? "border-b-2 border-saffron text-saffron-darker"
                : "text-muted-foreground hover:text-indigo-dark",
            )}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "Setup" && <SetupPanel onSelect={setHostelId} hostelId={hostelId} />}
      {tab === "Allocations" && hostelId && <AllocationsPanel hostelId={hostelId} />}
      {tab === "Mess" && hostelId && <MessPanel hostelId={hostelId} />}
      {tab === "Visitors" && hostelId && <VisitorsPanel hostelId={hostelId} />}
      {tab === "Discipline" && hostelId && <DisciplinePanel hostelId={hostelId} />}
      {tab === "Leaves" && hostelId && <LeavesPanel hostelId={hostelId} />}
      {tab === "Reports" && <ReportsPanel />}
    </div>
  );
}

// ---- Setup ---------------------------------------------------------------

function SetupPanel({ hostelId, onSelect }: { hostelId: number | null; onSelect: (id: number | null) => void }) {
  const qc = useQueryClient();
  const { data: hostels = [] } = useQuery({ queryKey: ["hostels"], queryFn: listHostels });
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<HostelKind>("boys");

  const [editingHostel, setEditingHostel] = useState<Hostel | null>(null);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [deleting, setDeleting] = useState<{ kind: "hostel"; item: Hostel } | { kind: "room"; item: Room } | null>(null);
  const refreshHostels = () => qc.invalidateQueries({ queryKey: ["hostels"] });
  const refreshRooms = () => qc.invalidateQueries({ queryKey: ["rooms", hostelId] });

  const newHostel = useMutation({
    mutationFn: () => createHostel({ code, name, kind }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hostels"] });
      setCode("");
      setName("");
    },
  });

  const { data: rooms = [] } = useQuery({
    queryKey: ["rooms", hostelId],
    queryFn: () => (hostelId ? listRooms(hostelId) : Promise.resolve([])),
    enabled: hostelId !== null,
  });

  const [number, setNumber] = useState("");
  const [capacity, setCapacity] = useState("2");
  const [fee, setFee] = useState("0");
  const newRoom = useMutation({
    mutationFn: () =>
      createRoom(hostelId!, {
        number,
        capacity: Number(capacity) || 1,
        monthly_fee: Number(fee) || 0,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms", hostelId] });
      setNumber("");
    },
  });

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Hostels</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-saffron-pale">
            {hostels.map((h) => (
              <li
                key={h.id}
                className={cn(
                  "flex cursor-pointer items-center justify-between py-2 text-sm",
                  hostelId === h.id && "rounded bg-saffron-pale/40 px-2",
                )}
                onClick={() => onSelect(h.id)}
              >
                <span className={cn("font-medium text-indigo-dark", !h.is_active && "opacity-60")}>
                  {h.name} <span className="text-xs text-muted-foreground">({h.code})</span>
                </span>
                <span className="flex items-center gap-1">
                  {!h.is_active && (
                    <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">inactive</span>
                  )}
                  <span className="rounded bg-teal-pale px-2 py-0.5 text-xs text-teal-dark">{h.kind}</span>
                  <button
                    type="button"
                    title="Edit hostel"
                    aria-label={`Edit ${h.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingHostel(h);
                    }}
                    className="rounded p-1.5 text-muted-foreground hover:bg-saffron-pale hover:text-indigo-dark"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    title="Delete hostel"
                    aria-label={`Delete ${h.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleting({ kind: "hostel", item: h });
                    }}
                    className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-3 grid grid-cols-4 gap-2">
            <Input placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} />
            <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={kind}
              onChange={(e) => setKind(e.target.value as HostelKind)}
            >
              <option value="boys">Boys</option>
              <option value="girls">Girls</option>
              <option value="mixed">Mixed</option>
            </select>
            <Button onClick={() => newHostel.mutate()} disabled={!code || !name || newHostel.isPending}>
              <Building className="mr-1 h-4 w-4" />
              Add
            </Button>
          </div>
          {newHostel.isError && (
            <p className="mt-2 text-xs text-destructive">{apiError(newHostel.error, "Could not add the hostel.")}</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Rooms</CardTitle>
          <CardDescription>{hostelId ? `${rooms.length} rooms` : "Pick a hostel above"}</CardDescription>
        </CardHeader>
        <CardContent>
          {hostelId && (
            <>
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="py-2">Number</th>
                    <th>Capacity</th>
                    <th>Occupied</th>
                    <th>Fee</th>
                    <th>Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rooms.map((r) => (
                    <tr key={r.id} className="border-t border-saffron-pale">
                      <td className="py-2 font-medium">{r.number}</td>
                      <td>{r.capacity}</td>
                      <td>
                        <span className={cn(
                          "rounded px-2 py-0.5 text-xs",
                          r.occupied >= r.capacity ? "bg-marigold-pale text-marigold-dark" : "bg-teal-pale text-teal-dark",
                        )}>
                          {r.occupied}
                        </span>
                      </td>
                      <td>₹{r.monthly_fee}</td>
                      <td>{r.status.replace("_", " ")}</td>
                      <td className="text-right whitespace-nowrap">
                        <button
                          type="button"
                          title="Edit room"
                          aria-label={`Edit room ${r.number}`}
                          onClick={() => setEditingRoom(r)}
                          className="rounded p-1.5 text-muted-foreground hover:bg-saffron-pale hover:text-indigo-dark"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          title="Delete room"
                          aria-label={`Delete room ${r.number}`}
                          onClick={() => setDeleting({ kind: "room", item: r })}
                          className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-3 grid grid-cols-4 gap-2">
                <Input placeholder="Number" value={number} onChange={(e) => setNumber(e.target.value)} />
                <Input
                  placeholder="Capacity"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                />
                <Input placeholder="Fee" value={fee} onChange={(e) => setFee(e.target.value)} />
                <Button onClick={() => newRoom.mutate()} disabled={!number || newRoom.isPending}>
                  <DoorOpen className="mr-1 h-4 w-4" />
                  Room
                </Button>
              </div>
              {newRoom.isError && (
                <p className="mt-2 text-xs text-destructive">{apiError(newRoom.error, "Could not add the room.")}</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
      {editingHostel && (
        <EditHostelDialog hostel={editingHostel} onClose={() => setEditingHostel(null)} onSaved={refreshHostels} />
      )}
      {editingRoom && (
        <EditRoomDialog room={editingRoom} onClose={() => setEditingRoom(null)} onSaved={refreshRooms} />
      )}
      {deleting && (
        <DeleteDialog
          what={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={() => {
            if (deleting.kind === "hostel") {
              refreshHostels();
              // The deleted hostel was the one picked: clear the pick.
              if (deleting.item.id === hostelId) onSelect(null);
            } else refreshRooms();
          }}
        />
      )}
    </div>
  );
}

// ---- Allocations ---------------------------------------------------------

function AllocationsPanel({ hostelId }: { hostelId: number }) {
  const qc = useQueryClient();
  const { data: rooms = [] } = useQuery({
    queryKey: ["rooms", hostelId],
    queryFn: () => listRooms(hostelId),
  });
  const [studentId, setStudentId] = useState("");
  const [roomId, setRoomId] = useState<string>("");
  const today = new Date().toISOString().slice(0, 10);
  const allocate = useMutation({
    mutationFn: () =>
      upsertAllocation({
        student_id: Number(studentId),
        room_id: Number(roomId),
        occupied_from: today,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms", hostelId] });
      setStudentId("");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Allocate student</CardTitle>
        <CardDescription>One allocation per student; re-allocating moves them.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-3 gap-3">
        <div>
          <Label>Student</Label>
          <StudentPicker value={studentId} onChange={(v) => setStudentId(v)} />
        </div>
        <div>
          <Label>Room</Label>
          <select
            className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          >
            <option value="">Select…</option>
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>
                {r.number} ({r.occupied}/{r.capacity})
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <Button onClick={() => allocate.mutate()} disabled={!studentId || !roomId || allocate.isPending}>
            <Plus className="mr-1 h-4 w-4" />
            Allocate
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---- Mess ----------------------------------------------------------------

function MessPanel({ hostelId }: { hostelId: number }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const { data: menus = [] } = useQuery({
    queryKey: ["mess", hostelId, date],
    queryFn: () => listMess(hostelId, date),
  });
  const [meal, setMeal] = useState<MealType>("breakfast");
  const [items, setItems] = useState("");
  const save = useMutation({
    mutationFn: () => upsertMess(hostelId, { menu_date: date, meal, items }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mess", hostelId, date] });
      setItems("");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mess menu</CardTitle>
        <CardDescription>Pick a date, edit each meal independently.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-3">
          <Input value={date} onChange={(e) => setDate(e.target.value)} />
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={meal}
            onChange={(e) => setMeal(e.target.value as MealType)}
          >
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="snacks">Snacks</option>
            <option value="dinner">Dinner</option>
          </select>
          <Input
            placeholder="Items (comma-separated)"
            value={items}
            onChange={(e) => setItems(e.target.value)}
          />
          <Button onClick={() => save.mutate()} disabled={!items || save.isPending}>
            <ChefHat className="mr-1 h-4 w-4" />
            Save
          </Button>
        </div>
        <ul className="divide-y divide-saffron-pale">
          {menus.map((m) => (
            <li key={m.id} className="flex items-center justify-between py-2 text-sm">
              <span className="rounded bg-saffron-pale px-2 py-0.5 text-saffron-darker">{m.meal}</span>
              <span className="flex-1 px-3">{m.items}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ---- Visitors ------------------------------------------------------------

function VisitorsPanel({ hostelId }: { hostelId: number }) {
  const qc = useQueryClient();
  const { data: visitors = [] } = useQuery({
    queryKey: ["visitors", hostelId],
    queryFn: () => listVisitors(hostelId),
  });
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [relation, setRelation] = useState("");
  const checkIn = useMutation({
    mutationFn: () =>
      checkInVisitor(hostelId, {
        student_id: Number(studentId),
        visitor_name: name,
        visitor_phone: phone || undefined,
        relation: relation || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["visitors", hostelId] });
      setName("");
      setPhone("");
      setRelation("");
    },
  });
  const checkOut = useMutation({
    mutationFn: (id: number) => checkOutVisitor(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visitors", hostelId] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Check in</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-5 gap-2">
          <StudentPicker value={studentId} onChange={(v) => setStudentId(v)} />
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Input placeholder="Relation" value={relation} onChange={(e) => setRelation(e.target.value)} />
          <Button onClick={() => checkIn.mutate()} disabled={!studentId || !name || checkIn.isPending}>
            <UserCheck className="mr-1 h-4 w-4" />
            In
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Visitors</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Visitor</th>
                <th>Student</th>
                <th>In</th>
                <th>Out</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visitors.map((v) => (
                <tr key={v.id} className="border-t border-saffron-pale">
                  <td className="py-2">
                    {v.visitor_name}
                    {v.relation && <span className="text-xs text-muted-foreground"> ({v.relation})</span>}
                  </td>
                  <td>#{v.student_id}</td>
                  <td>{new Date(v.in_at).toLocaleString()}</td>
                  <td>{v.out_at ? new Date(v.out_at).toLocaleString() : "—"}</td>
                  <td className="text-right">
                    {!v.out_at && (
                      <Button size="sm" variant="ghost" onClick={() => checkOut.mutate(v.id)}>
                        <UserMinus className="mr-1 h-3 w-3" />
                        Out
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Discipline ----------------------------------------------------------

function DisciplinePanel({ hostelId }: { hostelId: number }) {
  const qc = useQueryClient();
  const { data: rows = [] } = useQuery({
    queryKey: ["disc", hostelId],
    queryFn: () => listDisciplinary(hostelId),
  });
  const today = new Date().toISOString().slice(0, 10);
  const [studentId, setStudentId] = useState("");
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<DisciplinarySeverity>("note");
  const [description, setDescription] = useState("");
  const log = useMutation({
    mutationFn: () =>
      addDisciplinary(hostelId, {
        student_id: Number(studentId),
        incident_on: today,
        severity,
        title,
        description: description || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["disc", hostelId] });
      setStudentId("");
      setTitle("");
      setDescription("");
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Log incident</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-5 gap-2">
          <StudentPicker value={studentId} onChange={(v) => setStudentId(v)} />
          <Input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={severity}
            onChange={(e) => setSeverity(e.target.value as DisciplinarySeverity)}
          >
            <option value="note">Note</option>
            <option value="warning">Warning</option>
            <option value="suspension">Suspension</option>
          </select>
          <Input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Button onClick={() => log.mutate()} disabled={!studentId || !title || log.isPending}>
            <FileWarning className="mr-1 h-4 w-4" />
            Log
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Recent incidents</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-saffron-pale">
            {rows.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <span>{r.incident_on}</span>
                <span className="flex-1 px-3 font-medium text-indigo-dark">{r.title}</span>
                <span>#{r.student_id}</span>
                <span className={cn("rounded px-2 py-0.5 text-xs", SEVERITY_TONE[r.severity])}>{r.severity}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Leaves --------------------------------------------------------------

function LeavesPanel({ hostelId }: { hostelId: number }) {
  const qc = useQueryClient();
  const { data: leaves = [] } = useQuery({
    queryKey: ["hostel-leaves", hostelId],
    queryFn: () => listLeaves({ hostel_id: hostelId }),
  });
  const today = new Date().toISOString().slice(0, 10);
  const [studentId, setStudentId] = useState("");
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [reason, setReason] = useState("");
  const apply = useMutation({
    mutationFn: () =>
      applyLeave(hostelId, {
        student_id: Number(studentId),
        from_date: from,
        to_date: to,
        reason,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hostel-leaves", hostelId] });
      setStudentId("");
      setReason("");
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: "approved" | "rejected" }) =>
      decideLeave(id, { decision }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["hostel-leaves", hostelId] }),
  });
  const ret = useMutation({
    mutationFn: (id: number) => markReturned(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["hostel-leaves", hostelId] }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>File leave</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-5 gap-2">
          <StudentPicker value={studentId} onChange={(v) => setStudentId(v)} />
          <Input value={from} onChange={(e) => setFrom(e.target.value)} />
          <Input value={to} onChange={(e) => setTo(e.target.value)} />
          <Input placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button onClick={() => apply.mutate()} disabled={!studentId || !reason || apply.isPending}>
            <ClipboardList className="mr-1 h-4 w-4" />
            Apply
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Leaves</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Student</th>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {leaves.map((l) => (
                <tr key={l.id} className="border-t border-saffron-pale">
                  <td className="py-2">#{l.student_id}</td>
                  <td>{l.from_date}</td>
                  <td>{l.to_date}</td>
                  <td>{l.reason}</td>
                  <td>
                    <span className={cn("rounded px-2 py-0.5 text-xs", LEAVE_TONE[l.status])}>{l.status}</span>
                  </td>
                  <td className="space-x-1 text-right">
                    {l.status === "pending" && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => decide.mutate({ id: l.id, decision: "approved" })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => decide.mutate({ id: l.id, decision: "rejected" })}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {l.status === "approved" && (
                      <Button size="sm" variant="ghost" onClick={() => ret.mutate(l.id)}>
                        Returned
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Reports -------------------------------------------------------------

function ReportsPanel() {
  const { data } = useQuery({ queryKey: ["hostel-reports"], queryFn: reports });
  if (!data) return null;
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Tile label="Hostels" value={data.total_hostels} />
      <Tile label="Rooms" value={data.total_rooms} />
      <Tile label="Capacity" value={data.total_capacity} />
      <Tile label="Occupied" value={data.occupied} tone="marigold" />
      <Tile label="Available seats" value={data.available_seats} tone="teal" />
      <Tile label="Pending leaves" value={data.pending_leaves} tone="saffron" />
      <Tile label="Disciplinary records" value={data.open_disciplinary} />
    </div>
  );
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "marigold" | "saffron" | "teal";
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-1 font-display text-2xl",
            tone === "marigold" && "text-marigold-dark",
            tone === "saffron" && "text-saffron-darker",
            tone === "teal" && "text-teal-dark",
            !tone && "text-indigo-dark",
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
