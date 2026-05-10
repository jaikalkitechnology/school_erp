# Jaikalki School ERP — Phase Progress

Tracker for the 23-phase build defined in `school_erp_structure/`.

| Phase | Module | Status |
| ----- | ------ | ------ |
| 0 | Foundation (3 projects) | ✅ Done |
| 1 | Multi-Tenant Architecture | ✅ Done |
| 2 | Auth & RBAC (13 roles) | ✅ Done |
| 3 | Super Admin (Onboarding) | ⬜ |
| 4 | School Admin Foundation | ⬜ |
| 5 | Academic Setup | ⬜ |
| 6 | Student Information System | ⬜ |
| 7 | Teacher Management | ⬜ |
| 8 | Parent Module (Multi-Child) | ⬜ |
| 9 | Attendance | ⬜ |
| 10 | Mobile App Polish | ⬜ |
| 11 | Fee Management | ⬜ |
| 12 | Communication | ⬜ |
| 13 | Time Table & Substitution | ⬜ |
| 14 | Homework | ⬜ |
| 15 | Examination System | ⬜ |
| 16 | Report Cards | ⬜ |
| 17 | Library | ⬜ |
| 18 | Transport (GPS) | ⬜ |
| 19 | Hostel | ⬜ |
| 20 | Reports & Analytics | ⬜ |
| 21 | Subscription & Billing | ⬜ |
| 22 | Final Testing & Deployment | ⬜ |

## Phase 2 deliverables (shipped)

- **Auth schema** — `User`, `Role`, `Permission`, `RolePermission`, `UserRole`,
  `RefreshToken`, plus `Parent`, `Student` (stub), `ParentChildMapping`,
  `ParentSession`. Multi-role via the `UserRole` join.
- **Permission catalogue** — 60+ permissions across 14 categories (`tenant.*`,
  `platform.*`, `student.*`, `teacher.*`, `parent.*`, `attendance.*`,
  `exam.*`, `fee.*`, `communication.*`, `timetable.*`, `homework.*`,
  `library.*`, `transport.*`, `hostel.*`, `reports.*`).
- **System roles** — 14 roles (Super Admin L10 → Student L1) seeded per tenant
  with default grants. Catalogue lives in `app/core/rbac_catalog.py`.
- **Auth service** — bcrypt password hashing, JWT access (15 min) + refresh
  (30 days), refresh-token rotation with DB-backed revocation, logout that
  revokes a single session or all sessions for the user.
- **Auth endpoints** — `/v1/auth/login` (identifier + password + optional
  `subdomain` field), `/refresh`, `/logout`, `/me`, `/parent/children`,
  `/parent/select-child`, `/forgot-password` + `/reset-password` skeletons
  (OTP delivery in Phase 12).
- **RBAC dependencies** — `get_current_principal`, `require_roles(*)`,
  `require_permission(code)`, `require_super_admin()`. Token / subdomain
  mismatch → 403 (defense-in-depth).
- **Super Admin gating** — `/admin/tenants/*` and `/admin/plans` now require a
  super-admin token. School-admin tokens get a 403.
- **Seed defaults** — `python -m app.services.seed` provisions the platform
  tenant, demo school, and two default users:
  - `admin@jaikalki.com` / `Admin@123` (super_admin, subdomain=`platform`)
  - `admin@demo.school` / `School@123` (school_admin, subdomain=`demo`)
- **Super Admin React** — login page calls `/v1/auth/login`, persists the
  user/token in zustand, sidebar shows the user + sign-out button.
- **School Admin React** — same flow, subdomain detected from `?school=…` or
  the host; axios interceptor sends `X-Tenant-Subdomain` so the FastAPI
  middleware resolves the right tenant during local dev.
- **Flutter** — `AuthRepository` over `flutter_secure_storage`, `AuthCubit`
  with `bootstrap`/`login`/`logout`, login page collects subdomain +
  credentials, dashboard shows the authenticated user + has a sign-out
  action, router redirects on auth state.
- **Tests** — 29 tests passing: refresh rotation, replay-after-refresh
  rejection, logout revocation, tenant/token mismatch 403, super-admin gate,
  /me roles + permissions, plus all of Phase 1's tests now go through real
  super-admin auth.

## Phase 1 deliverables (shipped)

- **Tenant schema** — `Tenant`, `SubscriptionPlan`, `Subscription`,
  `TenantSettings`, `TenantUsageSnapshot` models. Alembic-generated initial
  migration `c3ee8dac75ef_phase1_tenant_schema.py`.
- **Tenant resolution** — `TenantMiddleware` now does a real DB lookup
  (subdomain or `X-Tenant-Id` header), 404s on unknown tenants, 403s on
  suspended ones, attaches a `TenantContext` to `request.state`.
- **Auto query filter** — every ORM query through `tenant_scoped_session`
  gets `WHERE tenant_id = :id` injected via `with_loader_criteria` /
  `do_orm_execute`. `platform_session` is the explicit super-admin escape
  hatch. `execution_options(unsafe_cross_tenant=True)` is the only other way
  to bypass.
- **Redis cache** — `TenantCache` namespaces every key under
  `tenant:{id}:`, eliminating cross-tenant cache hits.
- **Storage** — per-tenant dirs (Phase 0) + new `assert_storage_room()` guard
  enforces the plan's storage cap before saving.
- **Super Admin endpoints** — `GET/POST/PATCH /admin/tenants`, suspend,
  activate, `/health`, `/impersonate` (mints a 30-min JWT carrying
  `tenant_id` + `impersonation: true`). Read-only `/admin/plans`.
- **Seed script** — `python -m app.services.seed` plants the
  Basic/Standard/Premium plans + a `demo` tenant.
- **Super Admin React** — `/schools` page now lists, searches, creates, and
  toggles tenant status against the new APIs.
- **Tests** — 16 tests passing, including the cross-tenant isolation
  invariants (filtered session can't see other tenants, escape hatch works,
  suspended tenant blocked at the middleware).

## Phase 0 deliverables (shipped)

- **`school_erp_backend/`** — FastAPI app, async SQLAlchemy 2.0, tenant
  middleware, local file storage with per-tenant isolation, docker-compose
  (MySQL + Redis + phpMyAdmin), pytest smoke tests.
- **`school_erp_super_admin_web/`** — React 19 + Vite + Tailwind + shadcn-style
  primitives, login + dashboard with live API health probe, react-router +
  tanstack-query + zustand, port 5173.
- **`school_erp_school_admin_web/`** — Same stack, school-admin nav
  (students/teachers/attendance/timetable/exams/fees/communication/library/
  transport/settings), port 5174.
- **`school_erp_mobile/jaikalki/`** — Flutter app with Material 3 theme rooted
  in the Jaikalki design tokens (Fraunces + DM Sans), go_router, Dio API
  client, get_it DI, login → dashboard flow.
- Branding (saffron / marigold / teal / indigo on warm-white) sourced from
  `school_erp_designed/jaikalki-school-erp-design.html` and applied
  consistently across all three surfaces.
