# Jaikalki School ERP — Phase Progress

Tracker for the 23-phase build defined in `school_erp_structure/`.

| Phase | Module | Status |
| ----- | ------ | ------ |
| 0 | Foundation (3 projects) | ✅ Done |
| 1 | Multi-Tenant Architecture | ✅ Done |
| 2 | Auth & RBAC (13 roles) | ✅ Done |
| 3 | Super Admin (Onboarding) | ✅ Done (core) |
| 4 | School Admin Foundation | ✅ Done (core) |
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

## Phase 4 deliverables (shipped)

Bulk import + ID-card templates deferred (Phase 4.8 / 4.9 — UI-heavy, will
revisit when SIS lands in Phase 6).

- **Academic schema** — `Department`, `AcademicYear`, `AcademicTerm`,
  `ClassDef`, `Section`, `Subject`, `ClassSubject`, `Holiday`. All
  TenantBase, all auto-filtered. Migration `0febbee8d0cb`.
- **/v1/school-admin** endpoints (gated to school_admin / principal /
  vice_principal / coordinator):
  - `GET /dashboard` — students, teachers, classes, sections, subjects,
    departments, active year (with terms), storage usage.
  - `GET/PATCH /settings` — branding + school identity (writes to the
    Tenant row via the platform session, since Tenant isn't TenantBase).
  - Departments / Classes / Sections / Subjects / Holidays CRUD.
  - Academic years CRUD + `POST /academic-years/{id}/activate` (enforces
    one-active-at-a-time invariant).
  - `POST /academic-years/{id}/terms` — add a term to a year.
- **School Admin React** —
  - **Dashboard** rebuilt with live KPI tiles, active-year card, quick
    links to Org / Academic / Students / Teachers.
  - **Settings page** at `/settings` — every Tenant identity field
    editable, live colour swatches.
  - **Org page** at `/org` with tabbed Departments / Classes / Sections /
    Subjects panels.
  - **Academic page** at `/academic` for year + term + holiday management,
    one-click year activation.
  - Sidebar gets two new top-level entries (Org, Academic).
- **Tests** — 44 passing (6 new): dashboard endpoint, settings get/patch,
  full CRUD round-trip across departments/classes/sections/subjects/years/
  terms/holidays, single-active-year invariant, cross-tenant isolation
  (Other tenant cannot see Demo's department), super_admin token blocked
  from `/v1/school-admin/*` (lacks the staff roles).

## Phase 3 deliverables (shipped)

Core Super Admin slice. Razorpay billing + ticket system + master templates
deferred to their own dedicated phases (21, future, 5).

- **Audit log** — `audit_logs` table + `app/services/audit.py`. Every super
  admin action (`tenant.create / update / suspend / activate / trial_extend /
  plan_change / impersonate`, `plan.create / update`) writes a row with
  actor, ip, user-agent, summary, and a JSON metadata bag.
- **Plan CRUD** — `POST /admin/plans`, `PATCH /admin/plans/{id}`. Catalogue
  is now editable by the super admin without a code deploy.
- **Tenant lifecycle** — new endpoints: `POST /admin/tenants/{id}/extend-trial`
  (bumps `subscription_end`, lifts the tenant out of suspension if needed) and
  `POST /admin/tenants/{id}/change-plan` (resets limits + module set, lifts
  trials to active).
- **Tenant detail bundle** — `GET /admin/tenants/{id}/usage` rolls up storage
  + user count + plan limits in one round-trip.
- **Cross-school analytics** — `GET /admin/analytics/overview`: total/active
  /trial/suspended schools, total students + teachers, MRR (monthly-equivalent
  across active subscriptions), storage used, breakdowns by plan code and
  state.
- **Audit feeds** — `GET /admin/tenants/{id}/audit` and `GET /admin/audit`
  (with `action_prefix` filter).
- **Super Admin React** —
  - **Dashboard** rebuilt with live KPI tiles (schools / MRR / students /
    teachers), bar charts for plan + state mix, and a recent-schools list
    with deep links.
  - **7-step Onboarding Wizard** at `/schools/new` (info → plan → branding →
    academic → admin → modules → review).
  - **Tenant Detail** at `/schools/:id` with Info / Usage / Audit tabs, plan
    swap, trial extension, suspend / activate, info edit.
  - **Plans page** with toggle + create form.
  - **Audit page** with action-prefix filter.
- **Tests** — 38 passing (9 new): plan CRUD, duplicate plan code 409, plan
  update, trial extension, plan change limits, analytics overview shape,
  audit log records, tenant audit feed, tenant usage endpoint.

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
