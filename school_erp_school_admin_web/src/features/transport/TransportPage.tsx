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
  listBuses,
  listDrivers,
  listFuel,
  listMaintenance,
  listRoutes,
  listStops,
  pingTrip,
  replaceStops,
  startTrip,
  tripView,
  upsertAllocation,
  type TripDirection,
  type TripPhase,
} from "./api";

const TABS = ["Fleet", "Routes", "Live trip", "Billing", "Logs"] as const;
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
      {tab === "Live trip" && <LiveTripPanel />}
      {tab === "Billing" && <BillingPanel />}
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
  const newDriver = useMutation({
    mutationFn: () =>
      createDriver({ full_name: drvName, phone: drvPhone, license_number: drvLicense }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transport-drivers"] });
      setDrvName("");
      setDrvPhone("");
      setDrvLicense("");
    },
  });

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
          <CardDescription>{drivers.length} drivers</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-saffron-pale">
            {drivers.map((d) => (
              <li key={d.id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-medium text-indigo-dark">{d.full_name}</span>
                <span className="text-xs text-muted-foreground">{d.phone ?? "—"}</span>
                <span className="rounded bg-teal-pale px-2 py-0.5 text-xs text-teal-dark">{d.status}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 grid grid-cols-4 gap-2">
            <Input placeholder="Name" value={drvName} onChange={(e) => setDrvName(e.target.value)} />
            <Input placeholder="Phone" value={drvPhone} onChange={(e) => setDrvPhone(e.target.value)} />
            <Input
              placeholder="License #"
              value={drvLicense}
              onChange={(e) => setDrvLicense(e.target.value)}
            />
            <Button
              onClick={() => newDriver.mutate()}
              disabled={!drvName || !drvLicense || newDriver.isPending}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add
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
              <CardTitle>Allocate student</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Input
                  placeholder="Student ID"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                />
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
                <Input placeholder="Fee /mo" value={fee} onChange={(e) => setFee(e.target.value)} />
              </div>
              <Button onClick={() => allocate.mutate()} disabled={!studentId || allocate.isPending}>
                <MapPin className="mr-1 h-4 w-4" />
                Save allocation
              </Button>
            </CardContent>
          </Card>
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
