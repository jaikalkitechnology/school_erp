import { api } from "@/lib/api";

export type BusStatus = "active" | "under_maintenance" | "inactive";
export type DriverStatus = "active" | "on_leave" | "inactive";
export type TripPhase = "scheduled" | "in_progress" | "completed" | "cancelled";
export type TripDirection = "pickup" | "drop";
export type BoardingEvent = "boarded" | "deboarded" | "no_show";
export type MaintenanceKind = "service" | "repair" | "inspection";

export interface Bus {
  id: number;
  registration_number: string;
  code: string | null;
  capacity: number;
  model: string | null;
  year_of_make: number | null;
  insurance_expiry: string | null;
  fitness_expiry: string | null;
  status: BusStatus;
  notes: string | null;
}

export interface Driver {
  id: number;
  full_name: string;
  phone: string | null;
  license_number: string;
  license_expiry: string | null;
  user_id: number | null;
  status: DriverStatus;
}

export interface Route {
  id: number;
  code: string;
  name: string;
  bus_id: number | null;
  driver_id: number | null;
  is_active: boolean;
  student_count: number;
  stop_count: number;
}

export interface Stop {
  id: number;
  route_id: number;
  sequence: number;
  name: string;
  latitude: number | null;
  longitude: number | null;
  pickup_time: string | null;
  drop_time: string | null;
}

export interface Allocation {
  id: number;
  student_id: number;
  route_id: number;
  pickup_stop_id: number | null;
  drop_stop_id: number | null;
  fee_per_month: number;
  is_active: boolean;
}

export interface Trip {
  id: number;
  route_id: number;
  trip_date: string;
  direction: TripDirection;
  phase: TripPhase;
  started_at: string | null;
  completed_at: string | null;
  last_lat: number | null;
  last_lng: number | null;
  last_speed_kph: number | null;
  last_ping_at: string | null;
  next_stop?: Stop | null;
  eta_minutes?: number | null;
}

export interface Boarding {
  id: number;
  trip_id: number;
  student_id: number;
  stop_id: number | null;
  event: BoardingEvent;
  captured_at: string;
}

export interface Maintenance {
  id: number;
  bus_id: number;
  kind: MaintenanceKind;
  performed_on: string;
  next_due_on: string | null;
  odometer_km: number | null;
  cost: number;
  notes: string | null;
}

export interface Fuel {
  id: number;
  bus_id: number;
  fueled_on: string;
  litres: number;
  cost: number;
  odometer_km: number | null;
  notes: string | null;
}

const base = "/v1/school-admin/transport";

export const listBuses = async () => (await api.get<Bus[]>(`${base}/buses`)).data;
export const createBus = async (p: Partial<Bus> & { registration_number: string }) =>
  (await api.post<Bus>(`${base}/buses`, p)).data;
export const updateBus = async (id: number, p: Partial<Bus> & { registration_number: string }) =>
  (await api.patch<Bus>(`${base}/buses/${id}`, p)).data;

export const listDrivers = async () => (await api.get<Driver[]>(`${base}/drivers`)).data;
export const createDriver = async (
  p: Partial<Driver> & { full_name: string; license_number: string },
) => (await api.post<Driver>(`${base}/drivers`, p)).data;
export const updateDriver = async (
  id: number,
  p: Partial<Driver> & { full_name: string; license_number: string },
) => (await api.patch<Driver>(`${base}/drivers/${id}`, p)).data;

export const listRoutes = async () => (await api.get<Route[]>(`${base}/routes`)).data;
export const createRoute = async (p: Partial<Route> & { code: string; name: string }) =>
  (await api.post<Route>(`${base}/routes`, p)).data;
export const updateRoute = async (
  id: number,
  p: Partial<Route> & { code: string; name: string },
) => (await api.patch<Route>(`${base}/routes/${id}`, p)).data;

export const listStops = async (routeId: number) =>
  (await api.get<Stop[]>(`${base}/routes/${routeId}/stops`)).data;
export const replaceStops = async (
  routeId: number,
  stops: Array<Omit<Stop, "id" | "route_id">>,
) => (await api.put<Stop[]>(`${base}/routes/${routeId}/stops`, { stops })).data;

export const listAllocations = async (routeId: number) =>
  (await api.get<Allocation[]>(`${base}/routes/${routeId}/allocations`)).data;
export const upsertAllocation = async (p: {
  student_id: number;
  route_id: number;
  pickup_stop_id?: number;
  drop_stop_id?: number;
  fee_per_month?: number;
}) => (await api.post<Allocation>(`${base}/allocations`, p)).data;
export const deallocate = async (studentId: number) =>
  (await api.delete(`${base}/allocations/${studentId}`)).data;

export const startTrip = async (p: {
  route_id: number;
  trip_date: string;
  direction: TripDirection;
}) => (await api.post<Trip>(`${base}/trips/start`, p)).data;

export const tripView = async (tripId: number) =>
  (await api.get<Trip>(`${base}/trips/${tripId}`)).data;

export const pingTrip = async (tripId: number, p: {
  lat: number; lng: number; speed_kph?: number;
}) => (await api.post<Trip>(`${base}/trips/${tripId}/ping`, p)).data;

export const completeTrip = async (tripId: number) =>
  (await api.post<Trip>(`${base}/trips/${tripId}/complete`)).data;

export const recordBoarding = async (tripId: number, p: {
  student_id: number; stop_id?: number; event?: BoardingEvent;
}) => (await api.post<Boarding>(`${base}/trips/${tripId}/boardings`, p)).data;

export const listBoardings = async (tripId: number) =>
  (await api.get<Boarding[]>(`${base}/trips/${tripId}/boardings`)).data;

export const addMaintenance = async (p: Partial<Maintenance> & { bus_id: number; performed_on: string }) =>
  (await api.post<Maintenance>(`${base}/maintenance`, p)).data;
export const listMaintenance = async (busId: number) =>
  (await api.get<Maintenance[]>(`${base}/buses/${busId}/maintenance`)).data;

export const addFuel = async (p: Partial<Fuel> & { bus_id: number; fueled_on: string; litres: number; cost: number }) =>
  (await api.post<Fuel>(`${base}/fuel`, p)).data;
export const listFuel = async (busId: number) =>
  (await api.get<Fuel[]>(`${base}/buses/${busId}/fuel`)).data;

// ---- Phase 26: monthly transport invoice generator -----------------------

export interface MonthlyInvoiceResult {
  structure_id: number;
  created: number;
  skipped: number;
  period_start: string;
  period_end: string;
}

export const generateMonthlyTransportInvoices = async (p: {
  year: number;
  month: number;
  due_day?: number;
}) =>
  (await api.post<MonthlyInvoiceResult>(`${base}/invoices/generate-monthly`, p))
    .data;

// ---- Phase 26.3: admin live multi-bus map + trip history -----------------

export interface LiveTrip {
  trip_id: number;
  route_id: number;
  route_name: string | null;
  bus_registration: string | null;
  driver_name: string | null;
  driver_phone: string | null;
  direction: string | null;
  phase: TripPhase;
  last_lat: number | null;
  last_lng: number | null;
  last_speed_kph: number | null;
  last_ping_at: string | null;
  started_at: string | null;
}

export const listLiveTrips = async () =>
  (await api.get<LiveTrip[]>(`${base}/trips/live`)).data;

export interface TripHistoryRow {
  id: number;
  trip_date: string;
  direction: string | null;
  phase: TripPhase;
  route_id: number;
  route_name: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_minutes: number | null;
}

export const listTripHistory = async (daysBack = 14) =>
  (await api.get<TripHistoryRow[]>(`${base}/trips/history`, {
    params: { days_back: daysBack },
  })).data;

// ---- Phase 26.5: link Driver row to a transport_manager user account ---

export interface DriverCandidate {
  user_id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
  already_a_driver: boolean;
}

export const listDriverCandidates = async () =>
  (await api.get<DriverCandidate[]>(`${base}/drivers/candidates`)).data;
