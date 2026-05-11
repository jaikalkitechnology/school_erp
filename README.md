# Jaikalki School ERP

Multi-tenant SaaS school management platform — backend (FastAPI), two
React admin webs, a Flutter parent / staff mobile app, and a 23-phase
build that took it from an empty repo to a production-ready release.

| Status | Tests | Phases | License |
| ------ | ----- | ------ | ------- |
| ✅ All 23 phases done (core) | 166 passing | 0 → 22 | Proprietary — Jaikalki Technology Pvt Ltd |

## Repo layout

```
school_erp_backend/          # FastAPI 0.110, SQLAlchemy 2.0 async, Alembic, MySQL/SQLite
school_erp_super_admin_web/  # React 19 + Vite — Jaikalki internal: tenant + plan + billing + audit
school_erp_school_admin_web/ # React 19 + Vite — per-school admin: students, fees, exams, …
school_erp_mobile/jaikalki/  # Flutter 3 — parent + staff app (login, dashboard, notifications)
school_erp_structure/        # The original 23-phase plan + architecture docs
school_erp_designed/         # The Tailwind/HTML design mockups every UI ports
PHASE_PROGRESS.md            # What's done in each phase, what's deferred + why
DEPLOYMENT.md                # Production runbook (Docker + nginx + backups)
SECURITY.md                  # Tenant isolation + RBAC + pen-test coverage
.github/workflows/ci.yml     # CI: backend pytest, both webs tsc+build, Flutter analyze+test
```

## What's inside

A multi-tenant SaaS where Jaikalki is the platform and every school is a
tenant. One database, one backend deployment, every row tagged with
`tenant_id`. Reads go through a tenant-scoped session that injects
`WHERE tenant_id = :tid` automatically — see
[`SECURITY.md`](./SECURITY.md) for the full audit.

The 23 phases (in build order) cover: foundation → multi-tenant arch →
auth & RBAC (14 roles) → super admin onboarding → school setup → SIS →
teachers → parent portal → attendance → mobile polish → fees →
communication → timetable → homework → exams → report cards → library →
transport with GPS → hostel → reports & analytics → billing → final
testing & deployment. [`PHASE_PROGRESS.md`](./PHASE_PROGRESS.md) has the
per-phase deliverables.

## Quick start (local dev)

Backend:

```bash
cd school_erp_backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # SQLite default — no DB setup needed
alembic upgrade head
python -m app.services.seed       # creates the platform + demo tenants
uvicorn app.main:app --reload
```

Default users (change passwords immediately in production):

| Subdomain  | Email                  | Password    | Role         |
|------------|------------------------|-------------|--------------|
| `platform` | `admin@jaikalki.com`   | `Admin@123` | super_admin  |
| `demo`     | `admin@demo.school`    | `School@123`| school_admin |

Super-admin web (port 5173):

```bash
cd school_erp_super_admin_web
npm install
npm run dev
```

School-admin web (port 5174):

```bash
cd school_erp_school_admin_web
npm install
npm run dev
```

Mobile:

```bash
cd school_erp_mobile/jaikalki
flutter pub get
flutter run
```

## Tests

```bash
cd school_erp_backend
pytest -q
```

166 tests covering every phase plus 5 cross-tenant pen tests + an
end-to-end happy path (admit → attendance → fee → parent dashboard).
The CI workflow in `.github/workflows/ci.yml` runs the same suite plus
both webs' `tsc --noEmit` + `npm run build` and Flutter analyze+test on
every push.

## Production

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the runbook. The TL;DR:

```bash
cd school_erp_backend
cp .env.example .env  # fill in MySQL + secrets
docker compose -f docker-compose.prod.yml --profile migrate run --rm migrator
docker compose -f docker-compose.prod.yml up -d
```

Health probes:
- `GET /v1/livez` — liveness (process up; never touches deps)
- `GET /v1/readyz` — readiness (503 if DB or Redis is down)
- `GET /v1/health` — verbose human dashboard view

## Branding

Saffron `#E85D2E`, marigold `#FFB800`, teal `#0F766E`, indigo
`#1F1248`, warm-white `#FFFCF7`. Display font Fraunces, body DM Sans,
Hindi Noto Sans Devanagari, mono JetBrains Mono. The
[`school_erp_designed/`](./school_erp_designed/) HTML mockups are the
source of truth for every screen.

## Deferred (by design — not bugs)

These items were deliberately left out because they need real provider
accounts or a paying customer's specifics, not more code:

- Live Razorpay capture for B2B billing + parent fee payments (the data
  path is signature-verified end-to-end against a stub gateway).
- MSG91 SMS / SendGrid email / FCM push provider adapters (the
  `notification_outbox` queues every external delivery; consumers need
  real keys).
- Mobile UIs for Phases 11-21 (the Flutter app stops at Phase 10
  polish; a 2-3 week sprint adds fee/exam/transport screens).
- Drag-drop report card designer + custom report builder + roommate
  matching algorithm (UX-heavy; wait for the first school's spec).
- Recorded training videos + 10-device mobile QA (Phase 22 deferral).

See each phase section in `PHASE_PROGRESS.md` for the full list with
rationale.

## License

© Jaikalki Technology Pvt Ltd. All rights reserved.
