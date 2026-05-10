# Jaikalki School ERP — Security model

The platform is multi-tenant SaaS. Every request is filtered by tenant
*before* RBAC runs, and every read goes through a tenant-scoped session
that injects `WHERE tenant_id = :tid` automatically (see
`app/core/tenant_session.py`). This document is the audit trail for what
those guarantees cost when you ship.

## 1. Authentication

- Passwords are hashed with bcrypt (`passlib[bcrypt]`, work factor 12).
  The `bcrypt<4.0` pin in `requirements.txt` exists because passlib 1.7.x
  hashes a long sentinel during init, which bcrypt 4 rejects under its
  72-byte limit.
- Login is OTP-less password + subdomain. JWT access tokens are 15
  minutes; refresh tokens are 30 days, single-use (rotated on every
  `/v1/auth/refresh`), and DB-backed so revocation is immediate.
- `/v1/auth/logout` revokes the current refresh-token row. Pass
  `?all=true` to revoke every active session for the user.
- Failed login attempts increment `users.failed_login_count`; after 10
  consecutive failures the account is auto-disabled until an admin
  resets the counter.

## 2. Tenant isolation

- `TenantMiddleware` resolves every request to a `TenantContext` from
  one of: a wildcard subdomain match (`*.school.example.com`), an
  `X-Tenant-Subdomain` header, or an `X-Tenant-Id` header. Unknown
  tenants return 404 *before* the route handler sees them, so RBAC
  never runs for a non-existent school.
- Suspended tenants return 403 at the same layer, even with a valid
  token, so a non-paying school stops being reachable instantly.
- `tenant_scoped_session` attaches a `with_loader_criteria` filter that
  injects `WHERE tenant_id = :tid` on every `select / update / delete`
  against any `TenantBase` subclass. There is exactly one escape hatch:
  `execution_options(unsafe_cross_tenant=True)`, used only by the
  super-admin platform endpoints.
- Cache: `TenantCache` (Redis) namespaces every key under
  `tenant:{tid}:` so a cache hit on the wrong tenant is impossible.
- File storage: `app/core/file_storage.py` writes everything under
  `uploads/tenant_X/` and the `serve_file` route resolves the requested
  path against the tenant root (`Path.resolve()` + a `startswith` check)
  to block path traversal.
- Token / subdomain mismatch is a defense-in-depth 403:
  `get_current_principal` rejects a request whose JWT `tid` doesn't
  match the resolved `TenantContext.tenant_id`. See
  `tests/test_phase22_security_and_e2e.py::
  test_demo_token_with_other_subdomain_is_403`.

## 3. RBAC

- 14 system roles seeded per tenant with explicit permission grants
  (`app/core/rbac_catalog.py`). `super_admin` is platform-level only;
  it is **never** seeded into a school tenant, so a super-admin token
  cannot quietly read school data through `/v1/school-admin/*` (covered
  by `test_super_admin_token_blocked_from_school_admin_routes`).
- All endpoints declare their required roles via `require_roles(...)`
  or a permission via `require_permission(code)`. Endpoints with no
  RBAC dep are explicit (`/v1/health`, `/v1/auth/login`, etc.).

## 4. Input validation

- Every request body is a `pydantic` model. There are no `dict`-typed
  endpoints. JSON column writes (e.g. report-card layout, comms
  template body) are typed at the Pydantic layer.
- File uploads validate extension against an allow-list per category
  (`ALLOWED_EXTENSIONS_BY_CATEGORY`) and re-encode images via Pillow
  before saving — no arbitrary EXIF or polyglot files reach disk.

## 5. SQL injection / ORM safety

- Every query is a `select(Model).where(...)` SQLAlchemy expression.
  No `.execute(text(...))` calls accept user input; the only `text()`
  usage is in fixed migration ops or pure-DDL housekeeping.
- Search filters (Phase 6 student search, Phase 17 library) use
  `column.ilike(f"%{q}%")` against a Pydantic-bound `q: str` parameter
  — the bind parameter goes through psycopg/aiomysql escaping, not
  string concatenation.

## 6. Secrets + transport

- `JWT_SECRET_KEY`, DB password, and gateway secrets are loaded only
  from environment / `.env` (never committed). `.env.example` lists
  every variable; CI fails if any required key is missing.
- The Razorpay confirm endpoint verifies an HMAC-SHA256 signature
  against the stored gateway secret before crediting an invoice
  (`app/services/fees.py::confirm_online_payment`).
- TLS is terminated upstream of the backend; do not run uvicorn on a
  public IP without nginx / Caddy in front.

## 7. Rate limiting (operator's responsibility)

The backend deliberately does *not* rate-limit at the application
layer. Run nginx `limit_req_zone` (or your CDN's WAF) at:
- `/v1/auth/login` — 10 req/min per IP,
- `/v1/auth/refresh` — 60 req/min per IP,
- `/v1/parent/payments/*` — 30 req/min per IP.

## 8. Audit log

Every super-admin action (`tenant.create / update / suspend / activate /
trial_extend / plan_change / impersonate`, `plan.create / update`)
writes a row to `audit_logs` with actor + IP + UA + JSON metadata. View
under `/admin/audit` or per-tenant under `/admin/tenants/{id}/audit`.

## 9. Penetration test coverage (CI)

`tests/test_phase22_security_and_e2e.py` runs 5 cross-tenant tests on
every PR:
1. Demo token + `X-Tenant-Subdomain: other` → 403.
2. Demo admin cannot list `other`'s students.
3. Super-admin token cannot reach `/v1/school-admin/*`.
4. Unknown subdomain → 404 at middleware.
5. School-admin token cannot reach `/admin/billing/*`.

Plus `test_super_admin_blocked` cases scattered through every module's
test file — there are 12 of them as of Phase 22.

## 10. Reporting a vulnerability

Email `security@jaikalki.com` (PGP key on the website). We aim to
acknowledge within 48 hours and patch critical issues within 7 days.
Do not file public GitHub issues for security bugs.
