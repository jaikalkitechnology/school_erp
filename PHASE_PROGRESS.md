# Jaikalki School ERP — Phase Progress

Tracker for the 23-phase build defined in `school_erp_structure/`.

| Phase | Module | Status |
| ----- | ------ | ------ |
| 0 | Foundation (3 projects) | ✅ Done |
| 1 | Multi-Tenant Architecture | ⬜ |
| 2 | Auth & RBAC (13 roles) | ⬜ |
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
