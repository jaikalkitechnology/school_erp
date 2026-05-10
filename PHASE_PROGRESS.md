# Jaikalki School ERP — Phase Progress

Tracker for the 23-phase build defined in `school_erp_structure/`.

| Phase | Module | Status |
| ----- | ------ | ------ |
| 0 | Foundation (3 projects) | ✅ Done |
| 1 | Multi-Tenant Architecture | ✅ Done |
| 2 | Auth & RBAC (13 roles) | ✅ Done |
| 3 | Super Admin (Onboarding) | ✅ Done (core) |
| 4 | School Admin Foundation | ✅ Done (core) |
| 5 | Academic Setup | ✅ Done (core) |
| 6 | Student Information System | ✅ Done (core) |
| 7 | Teacher Management | ✅ Done (core) |
| 8 | Parent Module (Multi-Child) | ✅ Done (core) |
| 9 | Attendance | ✅ Done (core) |
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

## Phase 9 deliverables (shipped)

Auto-SMS/Push on absence (9.4) deferred to Phase 12 (communication);
biometric integration (9.9) is optional and stays out for now;
subject-wise period attendance (9.3) waits for Phase 13 (timetable).
The model already carries a `period` column so the same table covers
both modes.

- **Schema** — `student_attendance` (unique on tenant + student + date +
  period, indexed on section/date and class/date). Migration
  `64da452807fd`.
- **/v1/school-admin/attendance** (gated to school staff incl. teachers;
  mark mutations to school admin / principal / VP / coordinator / class
  teacher):
  - `GET /section/{id}` — daily roll for a section, returns a list of
    students with their saved status (or `present` default with an
    `unmarked` count) plus aggregate counts.
  - `POST /mark` — bulk mark-all roll-call. Default status applies to
    every student in the section; per-student `entries` overrides.
    Idempotent upsert across re-marks.
  - `GET /section/{id}/monthly` — per-student attendance %
    (present + late + 0.5 × half_day) over a calendar month.
  - `GET /defaulters` — students below a threshold % over a window,
    optional section filter.
  - `GET /student/{id}` — recent history (defaults to last 60 rows).
- **Parent-facing** — Phase 8 dashboard now fills `today_attendance` from
  the actual roll, and `GET /v1/parent/children/{id}/attendance` returns
  the per-child history (with the same parent-link guard as documents).
- **School Admin React** — new `/attendance` page with three tabs:
  - **Roll-call**: section + date pickers, "Mark all present" shortcut,
    per-student status toggle (`P / A / L / Lv / ½`) with brand tones,
    optional remarks per row, save with one click.
  - **Monthly**: section + year + month → per-student stats with
    attendance % (red below 75%) and working days.
  - **Defaulters**: threshold + section + date range → ranked list of
    low-attendance students.
- **Flutter** — `ParentRepository.attendance(...)` + an attendance card
  on the parent dashboard shows the latest 8 marks per selected child
  with brand-coloured status pills.
- **Tests** — 82 passing (8 new): unmarked roster default, default +
  per-student mix, idempotent re-mark, invalid student rejected,
  monthly attendance % math (50% / 100%), defaulter threshold filter,
  student history accuracy, parent-link guard on attendance history.

## Phase 8 deliverables (shipped)

Fee payment (8.6), bus tracking (8.8), comms / PTM / notifications / photo
gallery (8.5, 8.10, 8.11, 8.12) deferred to their owning phases (Phase 11
fees, Phase 18 transport, Phase 12 communications).

- **Schema** — `ParentChildMapping` extended with `relation` and
  `access_level`; new `LeaveApplication` table. Migration `00531624cc6a`.
- **Auto-link on admit** — `admit_student` now finds-or-creates a `Parent`
  + `ParentChildMapping` whenever the student row carries a parent phone
  or email, attaches the `parent` role to the user, and reuses the row
  for siblings (one parent record covers all their children).
- **/v1/parent** (gated to `parent` role only):
  - `GET /me`
  - `GET /children` — every child the parent is linked to with relation +
    access level + permissions.
  - `POST /select-child` — flips `ParentSession.current_child_id`.
  - `GET /dashboard/{student_id}` — pending leaves, document count,
    sibling ids, upcoming events. Stubs for attendance/homework/fees fill
    in as their owning phases ship.
  - `GET /children/{id}/documents` — read-only document vault for
    *linked* children only.
  - `GET /leave-applications` + `POST /leave-applications` (rejects
    `end_date < start_date`, scoped to linked children).
- **/v1/school-admin** parent management:
  - `POST /parents` creates a parent user + Parent row + grants the role.
  - `GET /students/{id}/parents`, upsert via
    `POST /students/{id}/parents`, `DELETE /students/{id}/parents/{mapping_id}`.
  - `GET /leave-applications` queue + `POST /{id}/decide` for school
    admin / principal / VP / class teacher to approve or reject.
- **School Admin React** — `ParentLinksPanel` lives in the Family tab of
  the student detail page: list current parents, create+link a new parent
  in one form, or attach an existing user-id; relation, access level, and
  permission checkboxes are editable on every link.
- **Flutter** — `ParentRepository` over Dio, `ChildrenCubit` that loads
  children + dashboard for the selected child. The dashboard page now
  detects parent users, shows a horizontal **child switcher** with
  selected-state styling, and renders a per-child stats grid that pulls
  from `/v1/parent/dashboard/{id}`. Non-parent users get the existing
  staff card.
- **Tests** — 74 passing (7 new): admit auto-creates parent + reuses
  for siblings, school admin can create + login parent users, the
  parent-facing endpoints (`me`, `children`, `select-child`,
  `dashboard`) work end-to-end, leave application full lifecycle
  (parent applies → school admin decides), parent cannot read another
  parent's child, school admin can link/unlink parents, super-admin
  token blocked from `/v1/parent/*`.

## Phase 7 deliverables (shipped)

Performance tracking + appraisal (7.7) deferred — needs exam results +
parent feedback to be meaningful (Phase 15 + Phase 12).

- **Schema** — `Teacher`, `TeacherSubject` (qualifications), `TeacherAttendance`.
  Migration `6a3e8f02e5fa`.
- **/v1/school-admin/teachers** endpoints (reads gated to all school staff;
  mutations to school admin / principal / vice principal):
  - List + filters (search, department, employment status) + pagination.
  - **Onboard** creates the underlying `User` + assigns role(s) from
    `{principal, vice_principal, coordinator, class_teacher,
    subject_teacher}` in one shot. Auto employee number `EMP-YY-NNNN`.
  - PATCH for profile + status updates.
  - `PUT /qualified-subjects` replaces the qualified-subject set in one
    call.
  - `POST /assign-section-subject` writes `SectionSubject.teacher_user_id`,
    finally lighting up the column added in Phase 5.
  - `POST /assign-class-teacher` writes `Section.in_charge_user_id` and
    flags the teacher as a class teacher.
  - `GET /workload` server-aggregates `weekly_periods` across all
    section-subject assignments and reports unique class+subject counts.
  - `POST /attendance` (idempotent upsert) + `POST /attendance/bulk` for
    daily roll-call.
  - `GET /substitution-pool` returns active, available teachers for a
    target date, sorted by `(present, ascending workload)`. Optional
    `subject_id` filter to constrain to qualified teachers.
- **School Admin React** —
  - **Teachers list** at `/teachers` with search + dept + status filters.
  - **Onboard form** at `/teachers/onboard` with role chips, qualification
    chip-list, and live validation.
  - **Teacher detail** at `/teachers/:id` with **Profile / Subjects /
    Classes / Workload / Attendance** tabs. Subjects tab is a one-tap
    qualification toggle; Classes tab picks a section then takes / clears
    section-subjects and (one-click) makes this teacher the class teacher;
    Workload tab shows period totals + a per-row schedule; Attendance tab
    has a date picker + status buttons + history.
- **Tests** — 67 passing (9 new): onboard creates a loginable user,
  duplicate email 409, workload sums section-subject `weekly_periods`,
  class-teacher assignment writes the section, qualified-subjects PUT is
  a true replace, attendance is idempotent, substitution pool ranks
  present teachers ahead of absent ones with lower workload first,
  super-admin token blocked from `/v1/school-admin/teachers`,
  cross-tenant isolation.

## Phase 6 deliverables (shipped)

Bulk Excel import (6.5) and PDF rendering of TC / Bonafide (6.8) deferred —
the data path and JSON payload are ready for both, the renderer lands when
report cards (Phase 16) needs the same plumbing.

- **Schema** — Phase 2's `students` stub promoted to a full SIS row with
  identity + academic + personal + family + medical + status + sibling
  group columns. New tables: `admissions` (funnel), `student_documents`.
  Migration `712d09e4f2d4`.
- **Admission service** — auto admission number (`ADM-YY-NNNN`),
  validates section⇄class match, auto-links siblings on shared
  `parent_phone` / `parent_email` into a stable `sibling_group_id`.
- **Search + filters** — `/v1/school-admin/students` accepts `q`,
  `class_def_id`, `section_id`, `status`, `limit`, `offset` and returns a
  paged result.
- **Detail bundle** — `GET /v1/school-admin/students/{id}` returns the full
  record + documents + sibling ids.
- **Promotion** — `POST /students/promote` skips inactive students and
  reports them in the `skipped` payload; updates `current_class_label`.
- **Withdrawal + TC** — `POST /students/{id}/withdraw` flips status +
  `is_active` + `exit_date`; `GET .../transfer-certificate` returns the
  JSON payload Phase 16 will render to PDF.
- **Documents** — add / verify / delete student-document slots (paths point
  at the per-tenant `uploads/` tree from Phase 0).
- **Manual sibling link** — `POST /students/link-siblings` with 2+ ids.
- **Admission funnel** — `/v1/school-admin/admissions` CRUD + stage
  transitions + one-click `POST /admissions/{id}/admit` to promote into a
  Student row.
- **School Admin React** —
  - **Students list** at `/students` with debounced search + class /
    section / status filters + pagination + status pills + sibling-group
    badges.
  - **Admit form** at `/students/admit` with auto-generated admission
    number when blank; class/section selectors are linked.
  - **Student detail** at `/students/:id` with **Personal / Academic /
    Family / Documents / History** tabs. Documents tab adds, verifies, and
    deletes document slots; Family tab links to siblings.
- **Tests** — 58 passing (9 new): admit + auto-number, section/class
  validation, sibling auto-link by phone, search + class filter, promotion
  skipping inactive, withdraw + TC payload, admission funnel → student,
  document attach + verify, cross-tenant isolation. Conftest extended to
  truncate `admissions` + `student_documents`.

## Phase 5 deliverables (shipped)

Student-class assignment (5.3) and teacher-subject mapping (5.4) ship with
their owning entities — Phase 6 (SIS) and Phase 7 (Teachers) — to avoid
forward-references.

- **Schema** — `House`, `SectionSubject`, `CalendarEvent`, `Syllabus`,
  `Chapter`. All TenantBase. Migration `156ae1cc14ed`.
- **/v1/school-admin/curriculum** endpoints (gated to school staff /
  teachers; mutations restricted to school admin / principal / VP /
  coordinator):
  - Houses CRUD.
  - Section-subject CRUD plus an idempotent
    `POST /section-subjects/bulk` that links many subjects to a section in
    one round-trip.
  - Calendar event CRUD with a `kind` enum (general / exam / sports /
    cultural / parent_teacher / holiday).
  - Syllabus CRUD per (year × class × subject) with chapter children.
    `GET /syllabi` returns each syllabus with a server-computed
    `overall_completion_pct` weighted by `expected_periods`.
  - `POST /syllabi/{id}/chapters` to add chapters.
  - `PATCH /chapters/{id}/progress` updates `completion_pct` and stamps
    `completed_on` automatically when it hits 100%.
- **School Admin React** — new `/curriculum` page with **Houses**,
  **Section subjects**, **Calendar**, **Syllabus** tabs. The section-
  subject panel is a one-tap toggle grid; the syllabus panel inlines
  chapter rows with progress sliders + an add-chapter row. New sidebar
  entry "Curriculum".
- **Tests** — 49 passing (5 new): house CRUD, idempotent bulk section-
  subject link, calendar event CRUD, weighted overall completion math
  (6×100 + 4×50 → 80%), super-admin token blocked from `/v1/school-admin/
  curriculum`. Conftest `_truncate_all` extended to cover Phase 4 + 5
  tables so tests don't bleed.

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
