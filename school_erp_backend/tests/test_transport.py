"""Phase 18 transport system tests."""

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
)


async def _login(subdomain: str, email: str, password: str) -> str:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={"identifier": email, "password": password, "subdomain": subdomain},
        )
        assert r.status_code == 200, r.text
        return r.json()["tokens"]["access_token"]


@pytest_asyncio.fixture
async def demo_admin_client(super_admin_token):
    token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def fleet(demo_admin_client):
    bus = (await demo_admin_client.post(
        "/v1/school-admin/transport/buses",
        json={"registration_number": "MH12-AB-1234", "capacity": 40},
    )).json()
    driver = (await demo_admin_client.post(
        "/v1/school-admin/transport/drivers",
        json={"full_name": "Ramesh", "phone": "+919900000080",
              "license_number": "MH-DR-001"},
    )).json()
    route = (await demo_admin_client.post(
        "/v1/school-admin/transport/routes",
        json={"code": "R1", "name": "North loop", "bus_id": bus["id"], "driver_id": driver["id"]},
    )).json()
    stops = (await demo_admin_client.put(
        f"/v1/school-admin/transport/routes/{route['id']}/stops",
        json={
            "stops": [
                {"sequence": 1, "name": "Park", "latitude": 18.50, "longitude": 73.85,
                 "pickup_time": "07:30:00"},
                {"sequence": 2, "name": "Market", "latitude": 18.52, "longitude": 73.86,
                 "pickup_time": "07:40:00"},
                {"sequence": 3, "name": "School gate", "latitude": 18.55, "longitude": 73.88,
                 "pickup_time": "07:55:00"},
            ],
        },
    )).json()
    return {"bus": bus, "driver": driver, "route": route, "stops": stops}


@pytest.mark.asyncio
async def test_bus_driver_route_setup(demo_admin_client, fleet):
    listing = (await demo_admin_client.get("/v1/school-admin/transport/routes")).json()
    assert any(r["code"] == "R1" for r in listing)
    one = next(r for r in listing if r["code"] == "R1")
    assert one["stop_count"] == 3
    assert one["student_count"] == 0

    dup = await demo_admin_client.post(
        "/v1/school-admin/transport/buses",
        json={"registration_number": "MH12-AB-1234", "capacity": 30},
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_allocate_student_and_stop_validation(demo_admin_client, fleet):
    f = fleet
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Kabir",
            "parent_phone": "+919900000081", "parent_email": "kabir@home.test",
            "father_name": "Test Parent",
        },
    )).json()
    bad = await demo_admin_client.post(
        "/v1/school-admin/transport/allocations",
        json={
            "student_id": student["id"], "route_id": f["route"]["id"],
            "pickup_stop_id": 99999,
        },
    )
    assert bad.status_code == 400

    ok = await demo_admin_client.post(
        "/v1/school-admin/transport/allocations",
        json={
            "student_id": student["id"], "route_id": f["route"]["id"],
            "pickup_stop_id": f["stops"][0]["id"],
            "drop_stop_id": f["stops"][2]["id"],
            "fee_per_month": 800,
        },
    )
    assert ok.status_code == 200, ok.text

    # Re-upsert (same student) is idempotent.
    again = await demo_admin_client.post(
        "/v1/school-admin/transport/allocations",
        json={
            "student_id": student["id"], "route_id": f["route"]["id"],
            "pickup_stop_id": f["stops"][1]["id"],
            "fee_per_month": 900,
        },
    )
    assert again.status_code == 200
    assert float(again.json()["fee_per_month"]) == 900.0
    assert again.json()["pickup_stop_id"] == f["stops"][1]["id"]


@pytest.mark.asyncio
async def test_trip_lifecycle_with_gps_and_eta(demo_admin_client, fleet):
    f = fleet
    today = date.today().isoformat()
    trip = (await demo_admin_client.post(
        "/v1/school-admin/transport/trips/start",
        json={"route_id": f["route"]["id"], "trip_date": today, "direction": "pickup"},
    )).json()
    assert trip["phase"] == "in_progress"

    # Send a ping near stop #2 (lat 18.52, lng 73.86) at 30 kph.
    pinged = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/ping",
        json={"lat": 18.521, "lng": 73.861, "speed_kph": 30},
    )
    assert pinged.status_code == 200

    view = (await demo_admin_client.get(
        f"/v1/school-admin/transport/trips/{trip['id']}"
    )).json()
    assert view["next_stop"]["name"] == "Market"
    assert view["eta_minutes"] is not None
    assert view["eta_minutes"] >= 0

    completed = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/complete"
    )
    assert completed.json()["phase"] == "completed"

    # Pings on a completed trip are rejected.
    bad = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/ping",
        json={"lat": 18.5, "lng": 73.85},
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_boarding_idempotent_and_invalid_student(demo_admin_client, fleet):
    f = fleet
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Lina", "parent_phone": "+919900000082",
              "parent_email": "lina@home.test", "father_name": "P"},
    )).json()
    today = date.today().isoformat()
    trip = (await demo_admin_client.post(
        "/v1/school-admin/transport/trips/start",
        json={"route_id": f["route"]["id"], "trip_date": today, "direction": "pickup"},
    )).json()
    a = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/boardings",
        json={"student_id": student["id"], "stop_id": f["stops"][0]["id"], "event": "boarded"},
    )
    assert a.status_code == 200
    # Same student again upserts (no duplicate row).
    b = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/boardings",
        json={"student_id": student["id"], "event": "deboarded"},
    )
    assert b.status_code == 200
    rows = (await demo_admin_client.get(
        f"/v1/school-admin/transport/trips/{trip['id']}/boardings"
    )).json()
    assert len(rows) == 1
    assert rows[0]["event"] == "deboarded"

    # Invalid student.
    bad = await demo_admin_client.post(
        f"/v1/school-admin/transport/trips/{trip['id']}/boardings",
        json={"student_id": 99999, "event": "boarded"},
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_maintenance_fuel_and_parent_view(demo_admin_client, fleet):
    f = fleet
    today = date.today().isoformat()
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Maya", "parent_phone": "+919900000083",
              "parent_email": "maya@home.test", "father_name": "P"},
    )).json()
    await demo_admin_client.post(
        "/v1/school-admin/transport/allocations",
        json={
            "student_id": student["id"], "route_id": f["route"]["id"],
            "pickup_stop_id": f["stops"][0]["id"],
            "fee_per_month": 700,
        },
    )

    # Maintenance + fuel logs.
    m = await demo_admin_client.post(
        "/v1/school-admin/transport/maintenance",
        json={"bus_id": f["bus"]["id"], "kind": "service",
              "performed_on": today, "cost": 2500},
    )
    assert m.status_code == 201
    fl = await demo_admin_client.post(
        "/v1/school-admin/transport/fuel",
        json={"bus_id": f["bus"]["id"], "fueled_on": today,
              "litres": 40, "cost": 4000},
    )
    assert fl.status_code == 201

    bus_logs = (await demo_admin_client.get(
        f"/v1/school-admin/transport/buses/{f['bus']['id']}/maintenance"
    )).json()
    assert len(bus_logs) == 1

    # Parent view round-trip.
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "maya@home.test", "subdomain": "demo",
              "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "maya@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        ok = await parent_ac.get(f"/v1/parent/children/{student['id']}/transport")
        assert ok.status_code == 200
        body = ok.json()
        assert body["route_name"] == "North loop"
        assert body["bus_registration"] == "MH12-AB-1234"
        assert body["driver_name"] == "Ramesh"


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/transport/buses")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_edit_and_delete_routes(demo_admin_client):
    c, base = demo_admin_client, "/v1/school-admin/transport/routes"
    a = (await c.post(base, json={"code": "E1", "name": "East loop"})).json()
    b = (await c.post(base, json={"code": "E2", "name": "West loop"})).json()

    # Edit: rename + deactivate; reusing another route's code is refused.
    r = await c.patch(f"{base}/{a['id']}", json={"code": "E1", "name": "East loop (new)", "is_active": False})
    assert r.status_code == 200 and r.json()["name"] == "East loop (new)" and r.json()["is_active"] is False
    r = await c.patch(f"{base}/{a['id']}", json={"code": "E2", "name": "East loop"})
    assert r.status_code == 409 and r.json()["detail"] == "Duplicate route code"

    # Re-saving stops with their ids updates them in place, so the
    # students picked up there keep their stop; a removed stop is cleared.
    gate, market = (await c.put(f"{base}/{a['id']}/stops", json={"stops": [
        {"sequence": 1, "name": "Gate"}, {"sequence": 2, "name": "Market"}]})).json()
    student = (await c.post("/v1/school-admin/students", json={"full_name": "Rider One"})).json()
    r = await c.post("/v1/school-admin/transport/allocations", json={
        "student_id": student["id"], "route_id": a["id"], "pickup_stop_id": gate["id"], "drop_stop_id": market["id"]})
    assert r.status_code == 200, r.text
    r = await c.put(f"{base}/{a['id']}/stops", json={"stops": [
        {"id": gate["id"], "sequence": 1, "name": "Main gate"}, {"sequence": 2, "name": "Park"}]})
    assert r.status_code == 200, r.text
    assert [(s["id"] == gate["id"], s["name"]) for s in r.json()] == [(True, "Main gate"), (False, "Park")]
    alloc = (await c.get(f"{base}/{a['id']}/allocations")).json()[0]
    assert alloc["pickup_stop_id"] == gate["id"] and alloc["drop_stop_id"] is None
    r = await c.put(f"{base}/{b['id']}/stops", json={"stops": [{"id": gate["id"], "sequence": 1, "name": "x"}]})
    assert r.status_code == 400

    # A route students ride can't be deleted until they're moved off it.
    r = await c.delete(f"{base}/{a['id']}")
    assert r.status_code == 409 and "Move them to another route first" in r.json()["detail"]
    assert (await c.delete(f"/v1/school-admin/transport/allocations/{student['id']}")).status_code == 204

    # Empty now: deleted along with its stops.
    assert (await c.delete(f"{base}/{a['id']}")).status_code == 204
    assert all(x["id"] != a["id"] for x in (await c.get(base)).json())
    assert (await c.delete(f"{base}/{a['id']}")).status_code == 404

    # A route that has run trips keeps its history: mark inactive instead.
    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from app.models.transport import Trip
    from sqlalchemy import select

    async with AsyncSessionLocal() as s:
        tid = (await s.execute(select(Tenant.id).where(Tenant.subdomain == "demo"))).scalar_one()
        s.add(Trip(tenant_id=tid, route_id=b["id"], trip_date=date.today(), direction="pickup"))
        await s.commit()
    r = await c.delete(f"{base}/{b['id']}")
    assert r.status_code == 409 and "Mark it inactive instead" in r.json()["detail"]
