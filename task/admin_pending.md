# 🖥️ Admin Panel — Pending

Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
App: `school_erp_school_admin_web`

Legend — ⏳ not started · 🔶 partial (works, has a gap)

---

## Navigation / structure

| Task | Status | What's needed |
|------|:------:|---------------|
| Fee Management sub-nav → real routes | 🔶 | Structure / Collection / Reports are tabs on one `/fees` page; split for deep-linking |
| Communication sub-nav → real routes | 🔶 | SMS / Email / Push / Circulars all point to one page |

## Validation still missing

| Task | Status | What's needed |
|------|:------:|---------------|
| Users & credentials: phone (10-digit) + email format | ⏳ | Partial guard; enforce on create/edit |
| Academic year / Term / Holiday: end_date ≥ start_date | ⏳ | Relational guard |
| Student aadhaar: 12-digit validation | ⏳ | Currently unbounded |
| Exam schedule: passing ≤ max + end ≥ start (submit-time) | 🔶 | Clamped on input; add relational guard |

## Pickers instead of raw IDs

| Task | Status | What's needed |
|------|:------:|---------------|
| Payroll "Generate payslip" User # → staff picker | ⏳ | Raw numeric id today |
| Certificates "Issue" Student # → student picker | ⏳ | Raw id today |
| Library Issue/Reservations Borrower ID → picker | ⏳ | Digits-only text today |

## Library — localStorage-only (need server tables)

| Task | Status | What's needed |
|------|:------:|---------------|
| Shelves & Racks | ⏳ | Real table + CRUD API (browser-local now) |
| Library Settings (loan days / fines policy) | ⏳ | Server-backed settings model |
| Import / Export | 🔶 | Export works client-side; bulk-import endpoint is a stub |
| Audit Logs | 🔶 | Synthesised from timestamps; dedicated audit table |
| Barcode Management | 🔶 | Monospace text labels; real Code-128/QR SVG |
| Inventory Verification | 🔶 | In-memory per walk-through; server-side sessions |

## Reports & depth

| Task | Status | What's needed |
|------|:------:|---------------|
| Reports: custom builder + scheduled email delivery | ⏳ | Beyond standard reports |
| Timetable builder depth / substitution UI | 🔶 | Polish |
| Report cards: portfolio + grade-scheme editor | ⏳ | |

## Backend validation (supports admin forms)

| Task | Status | What's needed |
|------|:------:|---------------|
| SIS/teacher phone fields format | ⏳ | Bare `Optional[str]` |
| Aadhaar 12-digit (backend) | ⏳ | |
| max_length caps on free-text columns | ⏳ | address, remarks, religion, caste… |

---

## 🚀 Deployment — required for ANY admin change to go live

| Task | Status | Detail |
|------|:------:|--------|
| Run Alembic migrations on prod | ⏳ | phase28 operations (16 tables) + `google_sub` |
| Rebuild + redeploy admin web | ⏳ | `npm install && npm run build` → deploy `dist/`, hard-refresh browsers |
| Google Cloud console config | ⏳ | JS origins per subdomain + `localhost:5173` for the Google button |
