# 🖥️ Admin Panel — Pending

Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
App: `school_erp_school_admin_web`

Legend — ⏳ not started · 🔶 partial (works, has a gap)

> Validation (users phone/email, academic date-order, student aadhaar, exam
> guards), the raw-ID pickers (payslip / certificate / library borrower), and
> backend phone/aadhaar/max_length caps are **DONE** — see `admin_complete.md`.
> What remains below are larger server-side features (new tables, migrations,
> report engine) that need dedicated, testable work.

---

## Navigation / structure

| Task | Status | What's needed |
|------|:------:|---------------|
| Fee Management sub-nav → real routes | 🔶 | Structure / Collection / Reports are tabs on one `/fees` page; split for deep-linking |
| Communication sub-nav → real routes | 🔶 | SMS / Email / Push / Circulars all point to one page |

## Library — localStorage-only (need server tables)

| Task | Status | What's needed |
|------|:------:|---------------|
| Shelves & Racks | ⏳ | Real table + CRUD API + migration (browser-local now) |
| Library Settings (loan days / fines policy) | ⏳ | Server-backed settings model + migration |
| Import / Export | 🔶 | Export works client-side; bulk-import endpoint is a stub |
| Audit Logs | 🔶 | Synthesised from timestamps; dedicated audit table |
| Barcode Management | 🔶 | Monospace text labels; real Code-128/QR SVG rendering |
| Inventory Verification | 🔶 | In-memory per walk-through; server-side verification sessions |

## Reports & depth

| Task | Status | What's needed |
|------|:------:|---------------|
| Reports: custom builder + scheduled email delivery | ⏳ | Report-builder engine, beyond standard reports |
| Timetable builder depth / substitution UI | 🔶 | Polish |
| Report cards: portfolio + grade-scheme editor | ⏳ | Project uploads, achievements, editable grade scheme |

## Backend validation (remaining)

| Task | Status | What's needed |
|------|:------:|---------------|
| Teacher schema phone fields format | ⏳ | Apply the same 10-digit guard used on SIS to teacher create/update |
| Exam-marks bounds mirrored into Pydantic | ⏳ | Defense-in-depth on the marks bulk schema |
