"""Phase 3 tests: plan CRUD, trial extension, plan change, analytics, audit."""

import pytest


@pytest.mark.asyncio
async def test_create_plan(auth_client):
    r = await auth_client.post(
        "/admin/plans",
        json={
            "code": "test_tier",
            "name": "Test Tier",
            "monthly_price": 99.0,
            "annual_price": 999.0,
            "student_limit": 50,
            "teacher_limit": 5,
            "storage_gb": 2,
            "sms_quota": 100,
            "modules_included": ["sis"],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "test_tier"


@pytest.mark.asyncio
async def test_duplicate_plan_code_409(auth_client):
    await auth_client.post(
        "/admin/plans",
        json={
            "code": "dup_tier",
            "name": "Dup",
            "monthly_price": 10,
            "annual_price": 100,
        },
    )
    r2 = await auth_client.post(
        "/admin/plans",
        json={
            "code": "dup_tier",
            "name": "Dup 2",
            "monthly_price": 10,
            "annual_price": 100,
        },
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_update_plan(auth_client):
    list_resp = await auth_client.get("/admin/plans")
    standard = next(p for p in list_resp.json() if p["code"] == "standard")
    r = await auth_client.patch(
        f"/admin/plans/{standard['id']}",
        json={"monthly_price": 30.0},
    )
    assert r.status_code == 200
    assert r.json()["monthly_price"] == 30.0


@pytest.mark.asyncio
async def test_extend_trial(auth_client):
    create = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Trial School",
            "school_code": "TRIAL-001",
            "subdomain": "trialx",
            "plan_code": "basic",
        },
    )
    tid = create.json()["id"]

    r = await auth_client.post(
        f"/admin/tenants/{tid}/extend-trial",
        json={"days": 14, "reason": "POC"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_change_plan_updates_limits(auth_client):
    create = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Plan Change School",
            "school_code": "PC-001",
            "subdomain": "pcschool",
            "plan_code": "basic",
        },
    )
    tid = create.json()["id"]
    assert create.json()["status"] == "trial"

    r = await auth_client.post(
        f"/admin/tenants/{tid}/change-plan",
        json={"plan_code": "premium"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "active"  # trial -> active on plan change
    assert body["storage_limit_mb"] == 100 * 1024


@pytest.mark.asyncio
async def test_analytics_overview(auth_client):
    r = await auth_client.get("/admin/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tenants"] >= 1
    assert isinstance(body["by_plan"], dict)
    assert isinstance(body["by_state"], dict)
    assert "mrr" in body


@pytest.mark.asyncio
async def test_audit_log_records_actions(auth_client):
    # Trigger an action that should produce an audit row.
    await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Audit School",
            "school_code": "AUD-001",
            "subdomain": "auditx",
            "plan_code": "basic",
        },
    )
    r = await auth_client.get("/admin/audit", params={"action_prefix": "tenant.create"})
    assert r.status_code == 200
    rows = r.json()
    assert any(row["action"] == "tenant.create" for row in rows)
    create_rows = [r for r in rows if r["target_type"] == "tenant"]
    assert any(r["actor_email"] == "admin@jaikalki.com" for r in create_rows)


@pytest.mark.asyncio
async def test_tenant_audit_feed(auth_client):
    create = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Feed School",
            "school_code": "FEED-001",
            "subdomain": "feedx",
            "plan_code": "basic",
        },
    )
    tid = create.json()["id"]
    await auth_client.post(f"/admin/tenants/{tid}/suspend")
    await auth_client.post(f"/admin/tenants/{tid}/activate")

    r = await auth_client.get(f"/admin/tenants/{tid}/audit")
    assert r.status_code == 200
    actions = {row["action"] for row in r.json()}
    assert {"tenant.create", "tenant.suspend", "tenant.activate"}.issubset(actions)


@pytest.mark.asyncio
async def test_tenant_usage_endpoint(auth_client):
    list_resp = await auth_client.get("/admin/tenants")
    demo = next(t for t in list_resp.json() if t["subdomain"] == "demo")

    r = await auth_client.get(f"/admin/tenants/{demo['id']}/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == demo["id"]
    assert "users_count" in body
    assert body["storage_limit_mb"] >= 0
