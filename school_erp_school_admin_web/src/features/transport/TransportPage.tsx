import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bus as BusIcon, MapPin, Plus, Play, Square, Wrench, Fuel } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  addFuel,
  addMaintenance,
  completeTrip,
  createBus,
  createDriver,
  createRoute,
  generateMonthlyTransportInvoices,
  listAllAllocations,
  listBuses,
  listDriverCandidates,
  listDrivers,
  listFuel,
  listLiveTrips,
  listMaintenance,
  listRoutes,
  listStops,
  listTripHistory,
  pingTrip,
  replaceStops,
  startTrip,
  tripView,
  upsertAllocation,
  type AllocationOverviewRow,
  type TripDirection,
  type TripPhase,
} from "./api";
import { listStudents } from "@/features/students/api";
import { api } from "@/lib/api";

const TABS = ["Fleet", "Routes", "Students", "Live map", "Live trip", "Billing", "History", "Logs"] as const;
type Tab = (typeof TABS)[number];

const PHASE_TONE: Record<TripPhase, string> = {
  scheduled: "bg-marigold-pale text-marigold-dark",
  in_progress: "bg-saffron-pale text-saffron-darker",
  completed: "bg-teal-pale text-teal-dark",
  cancelled: "bg-muted text-muted-foreground",
};

export function TransportPage() {
  const [tab, setTab] = useState<Tab>("Fleet");
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Phase 18 · Transport
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">Transport</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Manage buses, drivers, routes, stops, and student allocations. Run live trips with GPS
          pings + ETA, and keep maintenance + fuel logs.
        </p>
      </header>
      <nav className="flex gap-1 border-b border-saffron-pale">
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
      {tab === "Fleet" && <FleetPanel />}
      {tab === "Routes" && <RoutesPanel />}
      {tab === "Students" && <StudentsAssignedPanel />}
      {tab === "Live map" && <LiveMapPanel />}
      {tab === "Live trip" && <LiveTripPanel />}
      {tab === "Billing" && <BillingPanel />}
      {tab === "History" && <TripHistoryPanel />}
      {tab === "Logs" && <LogsPanel />}
    </div>
  );
}

// ---- Fleet (buses + drivers) --------------------------------------------

function FleetPanel() {
  const qc = useQueryClient();
  const { data: buses = [] } = useQuery({ queryKey: ["transport-buses"], queryFn: listBuses });
  const { data: drivers = [] } = useQuery({ queryKey: ["transport-drivers"], queryFn: listDrivers });

  const [reg, setReg] = useState("");
  const [capacity, setCapacity] = useState("40");
  const newBus = useMutation({
    mutationFn: () =>
      createBus({ registration_number: reg, capacity: Number(capacity) || 40 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-buses"] });
      setReg("");
    },
  });

  const [drvName, setDrvName] = useState("");
  const [drvPhone, setDrvPhone] = useState("");
  const [drvLicense, setDrvLicense] = useState("");
  // Selected candidate user — the transport_manager account this
  // Driver row will be linked to. Without it the driver app can't
  // tell *which* routes belong to *this* logged-in user.
  const [drvUserId, setDrvUserId] = useState<string>("");
  const { data: candidates = [] } = useQuery({
    queryKey: ["transport-driver-candidates"],
    queryFn: listDriverCandidates,
  });

  const newDriver = useMutation({
    mutationFn: () =>
      createDriver({
        full_name: drvName,
        phone: drvPhone,
        license_number: drvLicense,
        user_id: drvUserId ? Number(drvUserId) : undefined,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-drivers"] });
      qc.invalidateQueries({ queryKey: ["transport-driver-candidates"] });
      setDrvName("");
      setDrvPhone("");
      setDrvLicense("");
      setDrvUserId("");
    },
  });

  // Auto-fill the name / phone fields when the admin picks a candidate
  // so the most common case ("create transport_manager user → fleet
  // driver row") is one click of typing.
  function pickCandidate(uid: string) {
    setDrvUserId(uid);
    if (!uid) return;
    const c = candidates.find((x) => String(x.user_id) === uid);
    if (c) {
      if (!drvName) setDrvName(c.full_name);
      if (!drvPhone && c.phone) setDrvPhone(c.phone);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Buses</CardTitle>
          <CardDescription>{buses.length} buses</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-saffron-pale">
            {buses.map((b) => (
              <li key={b.id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-medium text-indigo-dark">{b.registration_number}</span>
                <span className="text-xs text-muted-foreground">cap {b.capacity}</span>
                <span className="rounded bg-teal-pale px-2 py-0.5 text-xs text-teal-dark">{b.status}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 grid grid-cols-3 gap-2">
            <Input placeholder="Reg #" value={reg} onChange={(e) => setReg(e.target.value)} />
            <Input
              placeholder="Capacity"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
            />
            <Button onClick={() => newBus.mutate()} disabled={!reg || newBus.isPending}>
              <BusIcon className="mr-1 h-4 w-4" />
              Add
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Drivers</CardTitle>
          <CardDescription>
            {drivers.length} driver{drivers.length === 1 ? "" : "s"}.
            Each Driver row is linked to a transport_manager user
            account so the driver app shows only the routes assigned
            to <em>that</em> login.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-saffron-pale">
            {drivers.map((d) => (
              <li key={d.id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-medium text-indigo-dark">
                  {d.full_name}
                  {d.user_id == null && (
                    <span className="ml-2 rounded bg-marigold-pale px-1.5 py-0.5 text-[10px] font-bold uppercase text-marigold-dark">
                      no login
                    </span>
                  )}
                </span>
                <span className="text-xs text-muted-foreground">
                  {d.phone ?? "—"}
                </span>
                <span className="rounded bg-teal-pale px-2 py-0.5 text-xs text-teal-dark">
                  {d.status}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-4 space-y-2 rounded-md border border-saffron-pale p-3">
            <Label className="text-xs uppercase tracking-wide">
              Add a driver
            </Label>

            {/* Step 1 — pick the user account this Driver row maps to. */}
            <div className="space-y-1.5">
              <Label>Driver account (transport_manager user)</Label>
              <select
                className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={drvUserId}
                onChange={(e) => pickCandidate(e.target.value)}
              >
                <option value="">— select a user —</option>
                {candidates
                  .filter((c) => !c.already_a_driver)
                  .map((c) => (
                    <option key={c.user_id} value={c.user_id}>
                      {c.full_name}
                      {c.phone ? ` · ${c.phone}` : ""}
                    </option>
                  ))}
              </select>
              {candidates.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No transport_manager users yet. Create one on{" "}
                  <strong>Users &amp; credentials</strong> with role
                  "transport_manager" first.
                </p>
              ) : candidates.every((c) => c.already_a_driver) ? (
                <p className="text-xs text-muted-foreground">
                  Every transport_manager user already has a Driver row.
                </p>
              ) : null}
            </div>

            {/* Step 2 — confirm / override the details that get
                copied onto the Driver row. */}
            <div className="grid grid-cols-3 gap-2">
              <Input
                placeholder="Name"
                value={drvName}
                onChange={(e) => setDrvName(e.target.value)}
              />
              <Input
                placeholder="Phone"
                value={drvPhone}
                onChange={(e) => setDrvPhone(e.target.value)}
              />
              <Input
                placeholder="License #"
                value={drvLicense}
                onChange={(e) => setDrvLicense(e.target.value)}
              />
            </div>
            <Button
              onClick={() => newDriver.mutate()}
              disabled={
                !drvName || !drvLicense || !drvUserId ||
                newDriver.isPending
              }
              className="w-full"
            >
              <Plus className="mr-1 h-4 w-4" />
              {newDriver.isPending ? "Saving…" : "Add driver + link login"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Routes + stops + allocations ---------------------------------------

function RoutesPanel() {
  const qc = useQueryClient();
  const { data: routes = [] } = useQuery({ queryKey: ["transport-routes"], queryFn: listRoutes });
  const { data: buses = [] } = useQuery({ queryKey: ["transport-buses"], queryFn: listBuses });
  const { data: drivers = [] } = useQuery({ queryKey: ["transport-drivers"], queryFn: listDrivers });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [busId, setBusId] = useState<string>("");
  const [driverId, setDriverId] = useState<string>("");
  const newRoute = useMutation({
    mutationFn: () =>
      createRoute({
        code,
        name,
        bus_id: busId ? Number(busId) : undefined,
        driver_id: driverId ? Number(driverId) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-routes"] });
      setCode("");
      setName("");
      setBusId("");
      setDriverId("");
    },
  });

  const [activeRoute, setActiveRoute] = useState<number | null>(null);
  const { data: stops = [] } = useQuery({
    queryKey: ["transport-stops", activeRoute],
    queryFn: () => (activeRoute ? listStops(activeRoute) : Promise.resolve([])),
    enabled: activeRoute !== null,
  });

  const [stopRows, setStopRows] = useState<{ name: string; pickup_time: string; lat: string; lng: string }[]>([]);
  const saveStops = useMutation({
    mutationFn: () =>
      replaceStops(
        activeRoute!,
        stopRows.map((r, i) => ({
          sequence: i + 1,
          name: r.name,
          pickup_time: r.pickup_time || null,
          drop_time: null,
          latitude: r.lat ? Number(r.lat) : null,
          longitude: r.lng ? Number(r.lng) : null,
        })),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transport-stops", activeRoute] }),
  });

  const [studentId, setStudentId] = useState("");
  const [pickupId, setPickupId] = useState<string>("");
  const [fee, setFee] = useState("0");
  const allocate = useMutation({
    mutationFn: () =>
      upsertAllocation({
        student_id: Number(studentId),
        route_id: activeRoute!,
        pickup_stop_id: pickupId ? Number(pickupId) : undefined,
        fee_per_month: Number(fee) || 0,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-routes"] });
      qc.invalidateQueries({
        queryKey: ["transport-route-allocations", activeRoute],
      });
      setStudentId("");
      setFee("0");
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Routes</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Code</th>
                <th>Name</th>
                <th>Bus</th>
                <th>Driver</th>
                <th>Stops</th>
                <th>Students</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r) => (
                <tr key={r.id} className="border-t border-saffron-pale">
                  <td className="py-2 font-medium">{r.code}</td>
                  <td>{r.name}</td>
                  <td>{r.bus_id ?? "—"}</td>
                  <td>{r.driver_id ?? "—"}</td>
                  <td>{r.stop_count}</td>
                  <td>{r.student_count}</td>
                  <td className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setActiveRoute(activeRoute === r.id ? null : r.id)}
                    >
                      {activeRoute === r.id ? "Hide" : "Stops + alloc"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 grid grid-cols-5 gap-2">
            <Input placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} />
            <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={busId}
              onChange={(e) => setBusId(e.target.value)}
            >
              <option value="">Bus</option>
              {buses.map((b) => (
                <option key={b.id} value={b.id}>{b.registration_number}</option>
              ))}
            </select>
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
            >
              <option value="">Driver</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>{d.full_name}</option>
              ))}
            </select>
            <Button onClick={() => newRoute.mutate()} disabled={!code || !name || newRoute.isPending}>
              <Plus className="mr-1 h-4 w-4" />
              Route
            </Button>
          </div>
        </CardContent>
      </Card>

      {activeRoute && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Stops</CardTitle>
              <CardDescription>Sequence is row order; replaces all on save.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {(stopRows.length === 0 ? stops.map((s) => ({
                  name: s.name,
                  pickup_time: s.pickup_time ?? "",
                  lat: s.latitude?.toString() ?? "",
                  lng: s.longitude?.toString() ?? "",
                })) : stopRows).map((row, i) => (
                  <li key={i} className="grid grid-cols-5 gap-2 text-sm">
                    <span className="text-xs text-muted-foreground">#{i + 1}</span>
                    <Input
                      placeholder="Stop name"
                      value={row.name}
                      onChange={(e) => {
                        const next = [...(stopRows.length ? stopRows : stops.map((s) => ({
                          name: s.name,
                          pickup_time: s.pickup_time ?? "",
                          lat: s.latitude?.toString() ?? "",
                          lng: s.longitude?.toString() ?? "",
                        })))];
                        next[i] = { ...next[i], name: e.target.value };
                        setStopRows(next);
                      }}
                    />
                    <Input
                      placeholder="07:30:00"
                      value={row.pickup_time}
                      onChange={(e) => {
                        const next = [...(stopRows.length ? stopRows : stops.map((s) => ({
                          name: s.name,
                          pickup_time: s.pickup_time ?? "",
                          lat: s.latitude?.toString() ?? "",
                          lng: s.longitude?.toString() ?? "",
                        })))];
                        next[i] = { ...next[i], pickup_time: e.target.value };
                        setStopRows(next);
                      }}
                    />
                    <Input
                      placeholder="Lat"
                      value={row.lat}
                      onChange={(e) => {
                        const next = [...(stopRows.length ? stopRows : stops.map((s) => ({
                          name: s.name,
                          pickup_time: s.pickup_time ?? "",
                          lat: s.latitude?.toString() ?? "",
                          lng: s.longitude?.toString() ?? "",
                        })))];
                        next[i] = { ...next[i], lat: e.target.value };
                        setStopRows(next);
                      }}
                    />
                    <Input
                      placeholder="Lng"
                      value={row.lng}
                      onChange={(e) => {
                        const next = [...(stopRows.length ? stopRows : stops.map((s) => ({
                          name: s.name,
                          pickup_time: s.pickup_time ?? "",
                          lat: s.latitude?.toString() ?? "",
                          lng: s.longitude?.toString() ?? "",
                        })))];
                        next[i] = { ...next[i], lng: e.target.value };
                        setStopRows(next);
                      }}
                    />
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="outline"
                  onClick={() =>
                    setStopRows([
                      ...(stopRows.length ? stopRows : stops.map((s) => ({
                        name: s.name,
                        pickup_time: s.pickup_time ?? "",
                        lat: s.latitude?.toString() ?? "",
                        lng: s.longitude?.toString() ?? "",
                      }))),
                      { name: "", pickup_time: "", lat: "", lng: "" },
                    ])
                  }
                >
                  <Plus className="mr-1 h-4 w-4" />
                  Add row
                </Button>
                <Button onClick={() => saveStops.mutate()} disabled={saveStops.isPending}>
                  Save stops
                </Button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Assign student to this bus</CardTitle>
              <CardDescription>
                Pick a student, choose their pickup stop + monthly fee.
                Each student can be on one route at a time — re-assigning
                overwrites the previous row.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <StudentPicker
                value={studentId}
                onChange={setStudentId}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="h-9 rounded border border-input bg-transparent px-2 text-sm"
                  value={pickupId}
                  onChange={(e) => setPickupId(e.target.value)}
                >
                  <option value="">Pickup stop</option>
                  {stops.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                <Input
                  placeholder="Fee /mo (₹)"
                  type="number"
                  value={fee}
                  onChange={(e) => setFee(e.target.value)}
                />
              </div>
              <Button
                onClick={() => allocate.mutate()}
                disabled={!studentId || allocate.isPending}
              >
                <MapPin className="mr-1 h-4 w-4" />
                {allocate.isPending ? "Saving…" : "Assign to bus"}
              </Button>
            </CardContent>
          </Card>

          <RouteRosterCard routeId={activeRoute!} />
        </div>
      )}
    </div>
  );
}

// ---- Live trip ----------------------------------------------------------

function LiveTripPanel() {
  const qc = useQueryClient();
  const { data: routes = [] } = useQuery({ queryKey: ["transport-routes"], queryFn: listRoutes });
  const [routeId, setRouteId] = useState<string>("");
  const [direction, setDirection] = useState<TripDirection>("pickup");
  const [tripId, setTripId] = useState<number | null>(null);
  const today = new Date().toISOString().slice(0, 10);

  const start = useMutation({
    mutationFn: () =>
      startTrip({ route_id: Number(routeId), trip_date: today, direction }),
    onSuccess: (t) => setTripId(t.id),
  });
  const { data: view, refetch } = useQuery({
    queryKey: ["trip-view", tripId],
    queryFn: () => tripView(tripId!),
    enabled: tripId !== null,
    refetchInterval: tripId !== null ? 5000 : false,
  });

  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [speed, setSpeed] = useState("25");
  const ping = useMutation({
    mutationFn: () => pingTrip(tripId!, { lat: Number(lat), lng: Number(lng), speed_kph: Number(speed) }),
    onSuccess: () => refetch(),
  });
  const finish = useMutation({
    mutationFn: () => completeTrip(tripId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trip-view", tripId] });
      setTripId(null);
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Start a trip</CardTitle>
          <CardDescription>One trip per (route, date, direction). Resume picks up the same row.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={routeId}
            onChange={(e) => setRouteId(e.target.value)}
          >
            <option value="">Route</option>
            {routes.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={direction}
            onChange={(e) => setDirection(e.target.value as TripDirection)}
          >
            <option value="pickup">Pickup</option>
            <option value="drop">Drop</option>
          </select>
          <Button onClick={() => start.mutate()} disabled={!routeId || start.isPending}>
            <Play className="mr-1 h-4 w-4" />
            Start
          </Button>
        </CardContent>
      </Card>

      {view && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Trip #{view.id}</CardTitle>
              <CardDescription>
                Route {view.route_id} · {view.direction} · {view.trip_date}
              </CardDescription>
            </div>
            <span className={cn("rounded px-2 py-0.5 text-xs", PHASE_TONE[view.phase])}>
              {view.phase}
            </span>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">Last ping: </span>
              {view.last_lat && view.last_lng
                ? `${view.last_lat}, ${view.last_lng} @ ${view.last_speed_kph ?? 0} kph`
                : "—"}
            </div>
            <div>
              <span className="text-muted-foreground">Next stop: </span>
              {view.next_stop ? `${view.next_stop.name} (~${view.eta_minutes ?? "?"} min)` : "—"}
            </div>
            <div className="grid grid-cols-4 gap-2">
              <Input placeholder="Lat" value={lat} onChange={(e) => setLat(e.target.value)} />
              <Input placeholder="Lng" value={lng} onChange={(e) => setLng(e.target.value)} />
              <Input placeholder="Speed kph" value={speed} onChange={(e) => setSpeed(e.target.value)} />
              <Button onClick={() => ping.mutate()} disabled={!lat || !lng || ping.isPending}>
                Ping
              </Button>
            </div>
            <Button variant="outline" onClick={() => finish.mutate()}>
              <Square className="mr-1 h-4 w-4" />
              Complete
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Maintenance + fuel logs -------------------------------------------

function LogsPanel() {
  const qc = useQueryClient();
  const { data: buses = [] } = useQuery({ queryKey: ["transport-buses"], queryFn: listBuses });
  const [busId, setBusId] = useState<string>("");
  const { data: maintenance = [] } = useQuery({
    queryKey: ["transport-maint", busId],
    queryFn: () => (busId ? listMaintenance(Number(busId)) : Promise.resolve([])),
    enabled: !!busId,
  });
  const { data: fuel = [] } = useQuery({
    queryKey: ["transport-fuel", busId],
    queryFn: () => (busId ? listFuel(Number(busId)) : Promise.resolve([])),
    enabled: !!busId,
  });

  const today = new Date().toISOString().slice(0, 10);
  const [mDate, setMDate] = useState(today);
  const [mCost, setMCost] = useState("0");
  const [mNotes, setMNotes] = useState("");
  const newMaint = useMutation({
    mutationFn: () =>
      addMaintenance({
        bus_id: Number(busId),
        kind: "service",
        performed_on: mDate,
        cost: Number(mCost) || 0,
        notes: mNotes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-maint", busId] });
      setMNotes("");
    },
  });

  const [fDate, setFDate] = useState(today);
  const [litres, setLitres] = useState("0");
  const [fCost, setFCost] = useState("0");
  const newFuel = useMutation({
    mutationFn: () =>
      addFuel({
        bus_id: Number(busId),
        fueled_on: fDate,
        litres: Number(litres) || 0,
        cost: Number(fCost) || 0,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-fuel", busId] });
      setLitres("0");
      setFCost("0");
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Pick a bus</CardTitle>
        </CardHeader>
        <CardContent>
          <select
            className="h-9 rounded border border-input bg-transparent px-2 text-sm"
            value={busId}
            onChange={(e) => setBusId(e.target.value)}
          >
            <option value="">Bus</option>
            {buses.map((b) => (
              <option key={b.id} value={b.id}>{b.registration_number}</option>
            ))}
          </select>
        </CardContent>
      </Card>
      {busId && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Maintenance</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-saffron-pale">
                {maintenance.map((m) => (
                  <li key={m.id} className="flex items-center justify-between py-2 text-sm">
                    <span>{m.performed_on}</span>
                    <span className="text-xs text-muted-foreground">{m.kind}</span>
                    <span>₹{m.cost}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 grid grid-cols-4 gap-2">
                <Input value={mDate} onChange={(e) => setMDate(e.target.value)} />
                <Input placeholder="Cost" value={mCost} onChange={(e) => setMCost(e.target.value)} />
                <Input placeholder="Notes" value={mNotes} onChange={(e) => setMNotes(e.target.value)} />
                <Button onClick={() => newMaint.mutate()} disabled={newMaint.isPending}>
                  <Wrench className="mr-1 h-4 w-4" />
                  Log
                </Button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Fuel</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-saffron-pale">
                {fuel.map((f) => (
                  <li key={f.id} className="flex items-center justify-between py-2 text-sm">
                    <span>{f.fueled_on}</span>
                    <span className="text-xs text-muted-foreground">{f.litres} L</span>
                    <span>₹{f.cost}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 grid grid-cols-4 gap-2">
                <Input value={fDate} onChange={(e) => setFDate(e.target.value)} />
                <Input placeholder="Litres" value={litres} onChange={(e) => setLitres(e.target.value)} />
                <Input placeholder="Cost" value={fCost} onChange={(e) => setFCost(e.target.value)} />
                <Button onClick={() => newFuel.mutate()} disabled={newFuel.isPending}>
                  <Fuel className="mr-1 h-4 w-4" />
                  Log
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ---- Billing (Phase 26 — monthly transport invoice generator) -----------

function BillingPanel() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [dueDay, setDueDay] = useState(10);
  const [result, setResult] = useState<null | {
    created: number;
    skipped: number;
    period_start: string;
    period_end: string;
  }>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () =>
      generateMonthlyTransportInvoices({ year, month, due_day: dueDay }),
    onSuccess: (data) => {
      setResult(data);
      setError(null);
    },
    onError: (err: any) =>
      setError(err?.response?.data?.detail ?? "Could not generate invoices"),
  });

  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BusIcon className="h-5 w-5" /> Monthly transport invoices
          </CardTitle>
          <CardDescription>
            Spin up a FeeInvoice for every active StudentTransport row with
            <code className="mx-1 rounded bg-muted px-1">fee_per_month &gt; 0</code>.
            Idempotent — re-running for the same month skips students already
            invoiced. Invoices show up in the parent's Fees screen alongside
            tuition.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label>Year</Label>
              <Input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value) || year)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Month</Label>
              <select
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
              >
                {months.map((m, i) => (
                  <option key={i} value={i + 1}>
                    {i + 1} · {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Due day</Label>
              <Input
                type="number"
                min={1}
                max={28}
                value={dueDay}
                onChange={(e) => setDueDay(Number(e.target.value) || dueDay)}
              />
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={() => run.mutate()} disabled={run.isPending}>
            {run.isPending ? "Generating…" : "Generate invoices"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>
              {result.period_start} → {result.period_end}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <span className="font-semibold text-teal-dark">
                {result.created}
              </span>{" "}
              new invoice{result.created === 1 ? "" : "s"} created.
            </p>
            <p>
              <span className="font-semibold text-muted-foreground">
                {result.skipped}
              </span>{" "}
              student{result.skipped === 1 ? "" : "s"} already invoiced for this
              month — left untouched.
            </p>
            <p className="pt-2 text-xs text-muted-foreground">
              Parents will see the new invoices on next pull-to-refresh of
              their Fees screen.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---- Live multi-bus map (Phase 26.3 — fleet dashboard) -----------------

function LiveMapPanel() {
  const { data: trips = [], refetch } = useQuery({
    queryKey: ["transport-live-trips"],
    queryFn: listLiveTrips,
    refetchInterval: 10_000,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" /> Live fleet
            </CardTitle>
            <CardDescription>
              Every bus currently on a trip. Auto-refreshes every 10 s.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {trips.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No buses are running right now.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Route</th>
                  <th className="px-2 py-2">Bus</th>
                  <th className="px-2 py-2">Driver</th>
                  <th className="px-2 py-2">Position</th>
                  <th className="px-2 py-2">Speed</th>
                  <th className="px-2 py-2">Last ping</th>
                </tr>
              </thead>
              <tbody>
                {trips.map((t) => (
                  <tr key={t.trip_id} className="border-b last:border-b-0">
                    <td className="px-2 py-2 font-medium text-indigo-dark">
                      {t.route_name ?? `Route #${t.route_id}`}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.bus_registration ?? "—"}
                    </td>
                    <td className="px-2 py-2">
                      <p>{t.driver_name ?? "—"}</p>
                      {t.driver_phone && (
                        <p className="font-mono text-xs text-muted-foreground">
                          {t.driver_phone}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.last_lat != null && t.last_lng != null ? (
                        <a
                          href={`https://maps.google.com/?q=${t.last_lat},${t.last_lng}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-teal-dark underline"
                        >
                          {t.last_lat.toFixed(4)}, {t.last_lng.toFixed(4)}
                        </a>
                      ) : (
                        "Awaiting GPS"
                      )}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.last_speed_kph != null
                        ? `${t.last_speed_kph.toFixed(0)} km/h`
                        : "—"}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.last_ping_at
                        ? new Date(t.last_ping_at).toLocaleTimeString()
                        : "—"}
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

// ---- Trip history (Phase 26.3) ------------------------------------------

function TripHistoryPanel() {
  const [days, setDays] = useState(14);
  const { data: trips = [], isLoading } = useQuery({
    queryKey: ["transport-trip-history", days],
    queryFn: () => listTripHistory(days),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" /> Recent trips
            </CardTitle>
            <CardDescription>
              Last {days} day{days === 1 ? "" : "s"} of trips across every
              route.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Label>Days</Label>
            <Input
              type="number"
              min={1}
              max={60}
              value={days}
              onChange={(e) => setDays(Number(e.target.value) || days)}
              className="w-20"
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : trips.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No trips in this window.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Route</th>
                  <th className="px-2 py-2">Direction</th>
                  <th className="px-2 py-2">Status</th>
                  <th className="px-2 py-2">Start</th>
                  <th className="px-2 py-2">End</th>
                  <th className="px-2 py-2">Duration</th>
                </tr>
              </thead>
              <tbody>
                {trips.map((t) => (
                  <tr key={t.id} className="border-b last:border-b-0">
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.trip_date}
                    </td>
                    <td className="px-2 py-2 font-medium text-indigo-dark">
                      {t.route_name ?? `Route #${t.route_id}`}
                    </td>
                    <td className="px-2 py-2 capitalize">
                      {t.direction ?? "—"}
                    </td>
                    <td className="px-2 py-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[11px] uppercase",
                          PHASE_TONE[t.phase],
                        )}
                      >
                        {t.phase}
                      </span>
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.started_at
                        ? new Date(t.started_at).toLocaleTimeString()
                        : "—"}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.completed_at
                        ? new Date(t.completed_at).toLocaleTimeString()
                        : "—"}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {t.duration_minutes != null
                        ? `${t.duration_minutes} min`
                        : "—"}
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

// ---- Student picker + route roster (Phase 26.4) -------------------------

function StudentPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const { data: hits = [] } = useQuery({
    queryKey: ["transport-student-search", q],
    queryFn: () => listStudents({ q, limit: 12 }),
    enabled: q.trim().length >= 2,
  });
  const rows = (hits as any).rows ?? (hits as any).items ?? hits;
  return (
    <div className="space-y-1">
      <Label>Student</Label>
      <div className="relative">
        <Input
          placeholder={value ? `Selected #${value}` : "Search by name or admission #…"}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
        {open && q.trim().length >= 2 && rows.length > 0 && (
          <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-background shadow-md">
            {rows.map((s: any) => (
              <li
                key={s.id}
                className="cursor-pointer px-3 py-2 text-sm hover:bg-saffron-pale"
                onClick={() => {
                  onChange(String(s.id));
                  setQ(`${s.full_name} (${s.admission_number ?? s.id})`);
                  setOpen(false);
                }}
              >
                <p className="font-medium text-indigo-dark">{s.full_name}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {s.admission_number ?? `#${s.id}`}
                  {s.section_id ? ` · Section ${s.section_id}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

interface AllocationRow {
  id: number;
  student_id: number;
  student_name: string | null;
  pickup_stop_id: number | null;
  drop_stop_id: number | null;
  fee_per_month: number;
}

const fetchAllocations = async (routeId: number) =>
  (await api.get<AllocationRow[]>(
    `/v1/school-admin/transport/routes/${routeId}/allocations`,
  )).data;

const deleteAllocation = async (studentId: number) => {
  await api.delete(`/v1/school-admin/transport/allocations/${studentId}`);
};

function RouteRosterCard({ routeId }: { routeId: number }) {
  const qc = useQueryClient();
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["transport-route-allocations", routeId],
    queryFn: () => fetchAllocations(routeId),
  });
  const remove = useMutation({
    mutationFn: deleteAllocation,
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["transport-route-allocations", routeId],
      });
      qc.invalidateQueries({ queryKey: ["transport-routes"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bus roster</CardTitle>
        <CardDescription>
          {rows.length} student{rows.length === 1 ? "" : "s"} currently on this
          bus. Click ✕ to remove an allocation.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No students assigned to this bus yet. Use the form on the left to
            add one.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Student</th>
                <th>Pickup</th>
                <th>Fee /mo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b last:border-b-0">
                  <td className="py-2">
                    <p className="font-medium text-indigo-dark">
                      {r.student_name ?? `Student #${r.student_id}`}
                    </p>
                    <p className="font-mono text-xs text-muted-foreground">
                      #{r.student_id}
                    </p>
                  </td>
                  <td className="font-mono text-xs">
                    {r.pickup_stop_id ?? "—"}
                  </td>
                  <td className="font-mono text-xs">
                    ₹{Number(r.fee_per_month).toFixed(0)}
                  </td>
                  <td className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => remove.mutate(r.student_id)}
                      disabled={remove.isPending}
                    >
                      ✕
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

// ---- Students tab — full bus roster + Assign dialog -----------------

function StudentsAssignedPanel() {
  const qc = useQueryClient();
  const { data: allocations = [], isLoading } = useQuery({
    queryKey: ["transport-all-allocations"],
    queryFn: listAllAllocations,
  });
  const { data: routes = [] } = useQuery({
    queryKey: ["transport-routes"],
    queryFn: listRoutes,
  });

  const [assignOpen, setAssignOpen] = useState(false);
  const [filterRoute, setFilterRoute] = useState<string>("");
  const [search, setSearch] = useState("");

  const remove = useMutation({
    mutationFn: deleteAllocation,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-all-allocations"] });
      qc.invalidateQueries({ queryKey: ["transport-routes"] });
    },
  });

  // Group rows by bus / route so the admin sees "Bus KA-01-1234 →
  // these 12 students, Bus KA-02-5678 → these 9 students, …".
  const filtered = allocations.filter((r) => {
    if (filterRoute && String(r.route_id) !== filterRoute) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.student_name.toLowerCase().includes(q) ||
      (r.admission_number ?? "").toLowerCase().includes(q) ||
      (r.parent_phone ?? "").includes(q) ||
      (r.bus_registration ?? "").toLowerCase().includes(q) ||
      (r.driver_name ?? "").toLowerCase().includes(q)
    );
  });

  const grouped = filtered.reduce(
    (acc, r) => {
      const key = `${r.route_id}`;
      if (!acc[key]) {
        acc[key] = {
          route_id: r.route_id,
          route_name: r.route_name,
          route_code: r.route_code,
          bus_registration: r.bus_registration,
          driver_name: r.driver_name,
          driver_phone: r.driver_phone,
          rows: [] as AllocationOverviewRow[],
        };
      }
      acc[key].rows.push(r);
      return acc;
    },
    {} as Record<
      string,
      {
        route_id: number;
        route_name: string | null;
        route_code: string | null;
        bus_registration: string | null;
        driver_name: string | null;
        driver_phone: string | null;
        rows: AllocationOverviewRow[];
      }
    >,
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BusIcon className="h-5 w-5" /> Students on buses
            </CardTitle>
            <CardDescription>
              {allocations.length} student
              {allocations.length === 1 ? "" : "s"} currently assigned to a
              bus across {Object.keys(grouped).length} route
              {Object.keys(grouped).length === 1 ? "" : "s"}.
            </CardDescription>
          </div>
          <Button onClick={() => setAssignOpen(true)}>
            <Plus className="mr-1 h-4 w-4" /> Assign student to bus
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Search by student / admission / parent phone / bus / driver…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-md"
            />
            <select
              className="h-9 rounded border border-input bg-transparent px-2 text-sm"
              value={filterRoute}
              onChange={(e) => setFilterRoute(e.target.value)}
            >
              <option value="">All routes</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} · {r.name}
                </option>
              ))}
            </select>
          </div>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : allocations.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No students assigned to any bus yet. Click{" "}
              <strong>Assign student to bus</strong> to add the first one.
            </p>
          ) : Object.keys(grouped).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No matches for the current filter.
            </p>
          ) : (
            Object.values(grouped).map((g) => (
              <div
                key={g.route_id}
                className="rounded-md border border-saffron-pale"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-saffron-pale bg-saffron-pale/30 px-3 py-2">
                  <div>
                    <p className="font-semibold text-indigo-dark">
                      {g.route_code ? `${g.route_code} · ` : ""}
                      {g.route_name ?? `Route #${g.route_id}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Bus {g.bus_registration ?? "—"} · Driver{" "}
                      {g.driver_name ?? "not assigned"}
                      {g.driver_phone ? ` · ${g.driver_phone}` : ""}
                    </p>
                  </div>
                  <span className="rounded-full bg-teal-pale px-2 py-0.5 text-xs font-bold text-teal-dark">
                    {g.rows.length} student{g.rows.length === 1 ? "" : "s"}
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2">Student</th>
                      <th>Parent</th>
                      <th>Pickup</th>
                      <th>Drop</th>
                      <th>Fee /mo</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.rows.map((r) => (
                      <tr
                        key={r.allocation_id}
                        className="border-t last:border-b-0"
                      >
                        <td className="px-3 py-2">
                          <p className="font-medium text-indigo-dark">
                            {r.student_name}
                          </p>
                          <p className="font-mono text-xs text-muted-foreground">
                            {r.admission_number ?? `#${r.student_id}`}
                          </p>
                        </td>
                        <td className="font-mono text-xs">
                          {r.parent_phone ?? "—"}
                        </td>
                        <td className="text-xs">
                          {r.pickup_stop_name ?? "—"}
                        </td>
                        <td className="text-xs">
                          {r.drop_stop_name ?? "—"}
                        </td>
                        <td className="font-mono text-xs">
                          ₹{Number(r.fee_per_month).toFixed(0)}
                        </td>
                        <td className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => remove.mutate(r.student_id)}
                            disabled={remove.isPending}
                          >
                            ✕
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {assignOpen && (
        <AssignStudentDialog
          routes={routes}
          onClose={() => setAssignOpen(false)}
          onSaved={() => {
            qc.invalidateQueries({
              queryKey: ["transport-all-allocations"],
            });
            qc.invalidateQueries({ queryKey: ["transport-routes"] });
            setAssignOpen(false);
          }}
        />
      )}
    </div>
  );
}

function AssignStudentDialog({
  routes,
  onClose,
  onSaved,
}: {
  routes: { id: number; code: string; name: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [routeId, setRouteId] = useState<string>("");
  const [studentId, setStudentId] = useState<string>("");
  const [pickupId, setPickupId] = useState<string>("");
  const [fee, setFee] = useState("0");

  const { data: stops = [] } = useQuery({
    queryKey: ["transport-stops", routeId || null],
    queryFn: () => listStops(Number(routeId)),
    enabled: routeId !== "",
  });

  const save = useMutation({
    mutationFn: () =>
      upsertAllocation({
        student_id: Number(studentId),
        route_id: Number(routeId),
        pickup_stop_id: pickupId ? Number(pickupId) : undefined,
        fee_per_month: Number(fee) || 0,
      }),
    onSuccess: onSaved,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg bg-background p-5 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-indigo-dark">
            Assign student to bus
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Bus / Route</Label>
            <select
              className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
              value={routeId}
              onChange={(e) => {
                setRouteId(e.target.value);
                setPickupId("");
              }}
            >
              <option value="">— pick a route —</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} · {r.name}
                </option>
              ))}
            </select>
          </div>
          <StudentPicker value={studentId} onChange={setStudentId} />
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1.5">
              <Label>Pickup stop</Label>
              <select
                className="h-9 w-full rounded border border-input bg-transparent px-2 text-sm"
                value={pickupId}
                onChange={(e) => setPickupId(e.target.value)}
                disabled={!routeId}
              >
                <option value="">— pick a stop —</option>
                {stops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Monthly fee (₹)</Label>
              <Input
                type="number"
                value={fee}
                onChange={(e) => setFee(e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={() => save.mutate()}
              disabled={!routeId || !studentId || save.isPending}
            >
              {save.isPending ? "Saving…" : "Assign to bus"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
