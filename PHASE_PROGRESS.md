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
| 10 | Mobile App Polish | ✅ Done (core) |
| 11 | Fee Management | ✅ Done (core) |
| 12 | Communication | ✅ Done (core) |
| 13 | Time Table & Substitution | ✅ Done (core) |
| 14 | Homework | ✅ Done (core) |
| 15 | Examination System | ✅ Done (core) |
| 16 | Report Cards | ✅ Done (core) |
| 17 | Library | ✅ Done (core) |
| 18 | Transport (GPS) | ✅ Done (core) |
| 19 | Hostel | ✅ Done (core) |
| 20 | Reports & Analytics | ✅ Done (core) |
| 21 | Subscription & Billing | ⬜ |
| 22 | Final Testing & Deployment | ⬜ |

## Phase 20 deliverables (shipped)

Drag-drop custom report builder, scheduled report email delivery, and
mobile UI deferred. The standard reports pipeline is wired (8 endpoints
+ a CSV exporter); a custom builder can layer on top by accepting a
JSON descriptor and dispatching to the same aggregator helpers.

Backend
- New `app/services/school_analytics.py` with cross-module
  aggregations: overview (students, teachers, classes, sections,
  attendance % today, fee collected this month, fee pending, overdue
  loans, by-class strength), N-day attendance trend with
  half-day-weighted %, fees overview (billed / collected / pending /
  overdue + by-method + by-category), exam analytics (per-section
  average + pass % + grade distribution from the default scale),
  library usage (issued today + overdue + most-loaned), transport
  summary (routes / buses / drivers / allocated / active trips), hostel
  summary (occupied / available / pending leaves), student directory
  with class + section filters.
- `/v1/school-admin/analytics`:
  - GET `/overview`, `/attendance-trend?days=`, `/fees`,
    `/exams[?exam_id=]`, `/library`, `/transport`, `/hostel`.
  - GET `/reports/students` (JSON) and `/reports/students.csv`
    (streaming CSV download with a `Content-Disposition: attachment`
    filename).

School Admin React
- New `/reports` page with **Overview / Attendance / Fees / Exams /
  Modules / Students** tabs. Recharts renders: bar chart for class
  strength, line chart for attendance trend with day-window selector,
  pie chart for fee methods + bar chart for fee categories, per-section
  exam table + grade distribution bar chart, library most-loaned
  horizontal bar, KPI tiles for transport + hostel. Students tab has
  class + section filters and a one-tap CSV download button that hits
  the streaming endpoint.
- New sidebar entry "Reports" between Hostel and Settings.

Tests: 6 new (148 total). Overview returns class strength rows,
attendance trend has 7 points + non-zero values once a roll is taken,
fees overview reflects newly generated invoices, library/transport/
hostel summaries return zeros on empty state, student JSON + CSV
report return the 3-row class with the expected columns and headers,
super_admin token blocked.

## Phase 19 deliverables (shipped)

Roommate-matching algorithm + warden mobile UI deferred. Allocation today is
manual ("put student X in room Y"); the schema is ready for a matcher to
populate it. The `/hostel` web UI covers wardens for now.

Backend
- New tables: `hostels`, `hostel_rooms`, `hostel_allocations`,
  `hostel_mess_menus`, `hostel_visitors`, `hostel_disciplinary`,
  `hostel_leaves`. Migration `8cb2e7ba59ad`.
  Hostels unique on (tenant + code); rooms on (tenant + hostel + number);
  allocations one-row-per-student; mess unique on
  (tenant + hostel + date + meal); leaves keyed by (hostel + student).
- `/v1/school-admin/hostel`:
  - Hostels + rooms CRUD; rooms list returns `occupied` per row.
  - `POST /allocations` upsert with capacity guard (rejects if room is
    already at capacity for *other* students), under-maintenance
    rejection, auto room status flip (full / available). Re-allocating
    the same student to the same room is idempotent.
  - `GET /rooms/{id}` returns the room + occupant list (name +
    admission #).
  - Mess menu: list-by-date, idempotent upsert per (date + meal).
  - Visitors: check-in writes `in_at`, `/{id}/checkout` writes `out_at`
    (rejects double-checkout); listing supports `open_only`.
  - Disciplinary records: log + list with optional `student_id` filter.
  - Hostel leaves (overnight pass, distinct from Phase 8 academic
    leaves): apply with `to_date >= from_date` guard, decide once
    (approved/rejected, second decide blocked), `mark_returned` only
    valid for approved leaves.
  - `/reports` returns 7 KPIs (hostels, rooms, capacity, occupied,
    available_seats, pending_leaves, open_disciplinary).
- `/v1/parent/children/{id}/hostel` returns the student's allocation
  + hostel/room + history of leaves with parent-link guard.

School Admin React
- New `/hostel` page with **Setup / Allocations / Mess / Visitors /
  Discipline / Leaves / Reports** tabs. The active hostel is picked
  once at the top and shared across tabs. Setup tab manages hostels +
  rooms with occupancy badges; Allocations binds a student ID to a
  room; Mess tab is a one-day-at-a-time editor; Visitors has a
  check-in form + per-row checkout; Discipline has a quick-log form
  + recent list; Leaves tab has the apply / approve / reject /
  returned lifecycle inline.
- Sidebar gets a new "Hostel" entry between Transport and Settings.

Tests: 6 new (142 total). Hostel + room setup with duplicate-number
409, allocation capacity-guard (3rd student into 2-cap room 400) +
idempotent re-allocation + occupant list, mess upsert by (date,meal)
+ visitor check-in/check-out + double-checkout 400 + disciplinary
log, full leave lifecycle (apply with bad dates 400, decide once,
re-decide 400, mark returned, parent-link-guarded child view),
reports endpoint totals, super_admin token blocked.

## Phase 18 deliverables (shipped)

Live mobile map view, native driver app, panic button + emergency
contacts, geo-fence alerts, and SMS-on-pickup deferred. The data path
is fully wired: GPS pings post to `/trips/{id}/ping`, the trip view
returns the closest stop + ETA so a real map UI can drop in next.
Boarding events already capture the QR-scan moment - rendering a
QR on a student card is a UX pass.

Backend
- New tables: `transport_buses`, `transport_drivers`, `transport_routes`,
  `transport_stops`, `transport_allocations`, `transport_trips`,
  `transport_trip_boardings`, `transport_maintenance_logs`,
  `transport_fuel_logs`. Migration `2088990f161a`.
  Buses unique on (tenant + registration); drivers on
  (tenant + license); routes on (tenant + code); allocations one-row-
  per-student; trips unique on (tenant + route + date + direction);
  boardings unique on (tenant + trip + student) so re-scans upsert.
- `/v1/school-admin/transport`:
  - Buses + drivers CRUD with status enums.
  - Routes CRUD; routes listing returns `student_count` + `stop_count`
    in one round-trip.
  - `PUT /routes/{id}/stops` replaces the whole stop list in one shot
    with a duplicate-sequence guard.
  - Allocations upsert (one allocation per student); validates the
    chosen stops belong to the route.
  - Trips: `POST /trips/start` (idempotent on the unique),
    `POST /trips/{id}/ping` writes the latest lat/lng/speed and auto-
    flips a SCHEDULED trip to IN_PROGRESS, `POST /trips/{id}/complete`,
    `GET /trips/{id}` returns the TripView with the closest stop +
    minute ETA via Haversine + last reported speed.
  - Boardings: idempotent QR-scan endpoint per (trip, student).
  - Maintenance + fuel CRUD with per-bus history listing.
- `/v1/parent/children/{id}/transport` returns the student's allocation,
  the bus reg + driver name/phone, and today's live trip view with
  ETA so the parent app can render a tracker. Parent-link guarded.

School Admin React
- New `/transport` page with **Fleet / Routes / Live trip / Logs**
  tabs. Fleet: add buses + drivers inline. Routes: row table with
  per-route stop editor (sequence is row order; replaces all on save)
  + per-student allocation form. Live trip: pick a route + direction,
  start, send GPS pings with auto-polling every 5 s, see closest stop
  + ETA, complete. Logs: per-bus maintenance + fuel ledgers.
- The /transport sidebar entry was already in place; the placeholder
  route was swapped for the live page.

Tests: 6 new (136 total). Bus + driver + route setup with duplicate
registration 409, allocation upsert + cross-route stop rejection +
idempotent re-allocation, trip lifecycle (start, ping, ETA via
Haversine to the closest stop, complete, ping-after-complete 400),
boarding upsert + invalid-student 400, maintenance + fuel logs +
parent-link-guarded transport view, super_admin token blocked.

## Phase 17 deliverables (shipped)

External ISBN lookup, barcode-image rendering, and a barcode-scanner UI
deferred. Barcodes are stored as text per copy and the UI accepts manual
entry; rendering them as Code-128 PNGs and wiring a webcam scanner is a
later UX pass.

Backend
- New tables: `library_books`, `library_copies`, `library_loans`,
  `library_reservations`. Migration `f8f6d98f330e`. Books are unique
  on (tenant + isbn); copies on (tenant + barcode); loans + reservations
  index `(borrower_kind, borrower_id)` for quick borrower history.
- `/v1/school-admin/library`:
  - Books CRUD (delete blocked while loans are active) with title /
    author / ISBN search + category filter; list returns
    `total_copies` + `available_copies` per row.
  - Copies single-add + bulk-add (auto-generated barcodes /
    accession numbers).
  - `POST /issue` validates the copy is `available`, the borrower is an
    active student (or trusted teacher user_id), defaults loan duration
    from the book and flips copy status to `issued`.
  - `POST /return` computes `(return_date - due_on).days * fine_per_day`,
    accepts `mark_lost`, validates `fine_paid <= fine_amount`, and
    promotes the first PENDING reservation for the same book to READY.
  - `POST /sweep-overdue` flags every ACTIVE loan whose `due_on < today`
    as `overdue` with the live fine.
  - `/loans` listing with status / borrower filters.
  - Reservations: place + auto-promote-to-READY when stock is on hand,
    duplicate guard, cancel (frees a held copy back to AVAILABLE).
  - `/reports` returns total / issued / available / overdue counts,
    outstanding fines, and a per-category breakdown.
- `/v1/parent/children/{id}/library` returns the child's lending
  history with parent-link guard.

School Admin React
- New `/library` page with **Catalog / Circulation / Reservations /
  Reports** tabs. Catalog has a search bar, an inline copy-counter,
  and an add-book form with default fine + loan-days. Circulation has
  one-shot issue, status-filtered loan table, sweep-overdue button,
  and one-tap return per row. Reservations has a place-form, status
  pills, and cancel buttons. Reports shows 5 KPI tiles + per-category
  table.
- Sidebar /library was already wired; the placeholder route was
  swapped for the live page.

Tests: 6 new (130 total). Book create + ISBN-duplicate 409 + search,
issue + double-issue 400 + return with computed fine, overdue sweep
flips status + bumps fine, reservation places + duplicate 409 +
auto-promotes to READY when a copy is returned, library reports
totals + parent-link-guarded child history, super_admin token blocked.

## Phase 16 deliverables (shipped)

Drag-drop visual template designer + email-on-publish deferred. Templates
today are JSON-layout records (board + flags) the renderer reads; a
WYSIWYG can land later without changing the data path. Email distribution
will reuse Phase 12's notification pipeline once the trigger is wired.

Backend
- New tables: `report_card_templates`, `co_curricular_grades`,
  `report_card_remarks`, `report_cards`. Migration `9b7c15b881e3`.
  Templates carry `board` (cbse/icse/state/custom) + JSON layout +
  single-default invariant. Cards persist a JSON `snapshot` so a parent
  always re-downloads the exact card that was generated, even if marks
  change later.
- `/v1/school-admin/report-cards`:
  - Templates CRUD (PUT upsert + DELETE) with default flip.
  - Co-curricular grades + class-teacher / principal remarks per
    (exam, student) — both list (by section) and upsert paths.
  - `POST /generate` materialises one card per active student in the
    section by reusing Phase 15's `section_results` aggregator,
    augmenting with co-curricular + remarks, rendering a reportlab PDF
    under `tenant_X/reports/report_cards/` and saving the relative
    path. Idempotent: re-running upserts the same row + re-renders the
    PDF. Optional `publish=true` flips status in one shot.
  - `POST /{exam_id}/sections/{id}/publish` to publish the whole
    section.
  - `GET /{exam_id}/sections/{id}` lists rendered cards.
  - `GET /{card_id}/pdf` streams the PDF (school admin).
- `/v1/parent/children/{id}/report-cards` lists published cards for
  linked children only; `/v1/parent/report-cards/{id}/pdf` re-checks
  the parent-link guard before streaming. Cross-child download 403.

School Admin React
- New `/report-cards` page with **Templates / Co-curricular & remarks /
  Generate / Cards** tabs:
  - Templates: list with default badge + add/update form (code, name,
    board, default toggle).
  - Co-curricular & remarks: pick exam + section → student selector
    backed by `examResults`, save area-grade-remarks rows (idempotent
    by area), separate textarea editor for class teacher + principal
    remarks.
  - Generate: pick exam + section + template + publish toggle, runs
    bulk and shows `generated / skipped` count.
  - Cards: lists per-section cards with %, grade, rank, status pill,
    one-tap PDF download (opens in a new tab) + Publish-all action.
- New sidebar entry "Report cards" between Exams and Fees.

Tests: 6 new (124 total). Template upsert with default-flip,
co-curricular + remarks upsert (idempotent by area), bulk generate
creates two cards with snapshots + PDFs (verified by `%PDF` magic
bytes), idempotent re-generate updates status to published, publish
section + parent-link-guarded download (cross-child 403), unknown
exam 404, super_admin token blocked.

## Phase 15 deliverables (shipped)

Online MCQ exams, question bank, hall ticket PDFs, and mobile exam-taking
deferred — those are dedicated UX flows that ride better on top of the
written-marks pipeline once Phase 16 (Report Cards) lands the rendering
infrastructure. The data path is complete: exam → exam-subjects (per
class) → bulk marks → results aggregator with grading + ranking →
publish → parent-link-guarded child results.

Backend
- New tables: `exams`, `exam_subjects`, `exam_marks`, `grade_scales`.
  `Exam` unique on (tenant + year + name); `ExamSubject` unique on
  (tenant + exam + class + subject); `ExamMarks` unique on (tenant +
  exam_subject + student); `GradeScale` carries JSON `bands` and a
  single-default invariant. Migration `40b1287bddda`.
- `/v1/school-admin/exams`:
  - GET / POST exams (validates start &lt; end, default max marks).
  - POST `/{id}/publish` (idempotent; flips `status=published`).
  - GET / POST exam-subjects (passing &lt;= max guard, duplicate 400).
  - GET `/exam-subjects/{id}/roster?section_id=` returns the section
    roll with any saved marks.
  - POST `/marks/bulk` upserts marks per (exam_subject, student).
    Validates obtained &lt;= max, derives status when not provided
    (absent / pass / fail by passing-mark threshold). Invalid student
    400.
  - GET `/{id}/results?section_id=` aggregates per-student totals,
    percentage, overall grade (from default scale), overall status
    (any-absent → absent, any-fail → fail, else pass), and
    `rank_in_section` with ties sharing the same rank.
- `/v1/school-admin/grade-scales` GET + PUT (sorts bands desc, enforces
  one default per tenant).
- `/v1/parent/children/{id}/exam-results` returns published results for
  linked children only; cross-child access 403.

School Admin React
- New `/exams` page with **Exams / Marks entry / Results / Grade scale**
  tabs:
  - Exams: create form, list with status pills + publish, schedule
    (class × subject × max × passing) form when an exam is selected.
  - Marks entry: pick exam → exam-subject → section, edit roster table
    inline (marks + status + remarks) with overflow validation, save
    in one shot.
  - Results: pick exam + section, ranked table with total / % /
    overall grade / overall status pills.
  - Grade scale: bands editor (min_pct + grade rows) with
    is_default toggle.

Tests: 6 new (118 total). Exam + subject setup with passing&gt;max
rejection, marks bulk over-mark 400 + valid round-trip with absent
status, grade scale + ranked results with tie / absent precedence
(Aarav 90% A+ rank 1, Bina 40% C rank 2, Chitra absent rank 3),
publish + parent-link guarded child results with cross-child 403,
invalid student 400, super_admin token blocked.

## Phase 14 deliverables (shipped)

Plagiarism detection + file-attachment upload UI deferred. Attachments
ride as JSON path arrays today; Phase 0's `/v1/uploads` already accepts
files - the React UI just needs to call it.

Backend
- New tables: `homework_assignments`, `homework_submissions` (unique on
  tenant + homework + student). Migration `2744bfd82acc`.
- `/v1/school-admin/homework` (gated to teachers + admins):
  - List by `section_id` or `teacher_user_id`.
  - POST creates with `assigned_on` defaulting to today; rejects past
    `due_date`.
  - PATCH updates title / description / due_date / max_marks /
    attachments. DELETE is admin-only.
  - `GET /{id}/submissions` and `GET /{id}/report` show per-student
    submission status (submitted / late / missing) + counts.
  - `POST /submissions/{id}/grade` writes marks + feedback, rejects
    over-mark.
- `/v1/parent/children/{id}/homework` and
  `POST .../homework/submit` for parent-led submissions on behalf of
  the child. Late submits get flagged automatically. Re-submit after a
  grade returns 409.
- Phase 8 `ChildDashboard.pending_homework` now actually counts open
  homework for the child's section.

School Admin React
- New `/homework` page: section picker, create-form, list of homework
  with click-to-drill-down detail. Detail panel shows the per-student
  status table with inline grading (marks + feedback inputs); already
  graded rows are read-only.

Tests: 7 new (112 total). Past-due-date rejection on create, parent
submit + teacher grade round-trip with overmark 400, late-submission
flag, status report counts, dashboard pending_homework, parent cross-
child block, re-submit-after-grade 409.

## Phase 13 deliverables (shipped)

Auto generator (constraint solver) + PDF export deferred. The grid editor
+ conflict detector is the manual flow; the rest of the schema is ready
for an optimiser to fill in.

Backend
- New tables: `PeriodDef` (one row per weekday × period number),
  `TimetableEntry` (unique on tenant + section + day + period),
  `Substitution` (unique on tenant + date + section + period). Migration
  `b8c43d8b501a`.
- `/v1/school-admin/timetable`:
  - Periods CRUD with start-before-end validation.
  - `GET /sections/{id}` returns the saved cells; `PUT` replaces the
    whole grid in one shot. The save runs a tenant-wide conflict check
    against every other section's grid - if any cell would put a
    teacher in two places at the same slot, the save returns `saved=0`
    + a list of `conflicts` rather than partial-write.
  - `GET /teachers/{user_id}` returns that teacher's own weekly view.
  - `POST /substitutions/suggest` walks the absent teacher's day-of-week
    schedule and ranks per-period substitute candidates (active +
    available + present + free + qualified for the subject when known).
  - `POST /substitutions` assigns a sub for a date+section+period;
    blocks if the substitute is already booked at the same slot.
  - `POST /{id}/complete` and `POST /{id}/cancel`.

School Admin React
- New `/timetable` page with **Section grid / Substitutions** tabs.
  The grid editor is a Mon-Sat × 8-period table where each cell exposes
  subject + teacher + room selectors. Save is single-button; conflicts
  surface as a destructive banner with the offending day/period and
  conflicting section. Substitutions tab picks a date + absent teacher,
  shows ranked suggestions per period with one-tap "Assign" buttons,
  plus a list of that day's substitutions with complete/cancel actions.

Tests: 8 new (105 total). Period CRUD with start-before-end check,
section grid save + conflict detection across sections, in-payload
duplicate cell rejection, teacher view aggregates correctly, sub
suggestion picks free + qualified candidate, sub assignment blocked
when substitute is busy at the same slot, full assign / complete /
cancel lifecycle, super_admin token blocked.

## Phase 12 deliverables (shipped)

Live SMS / WhatsApp / FCM push delivery deferred — they need real
provider credentials (MSG91 / Twilio / SendGrid / Firebase). The data
path is fully wired: every external channel writes a queued row to
`notification_outbox` that real adapters can consume.

Backend
- New tables: `NotificationTemplate`, `Announcement`, `Notification`,
  `NotificationOutbox`, `Message` (direct 1-1). Migration `f2b86b5c2688`.
- Channel abstraction in `app/services/comms.py`:
  - `Channel.IN_APP` writes a `Notification` row directly.
  - `SMS / EMAIL / WHATSAPP / PUSH` write a `NotificationOutbox` row
    with `status=queued` (or `skipped` if the user has no address).
- `notify(template_code, recipients, context)` formats `{{key}}`
  substitutions against the picked template, fans out across the
  template's channels.
- Audience resolver: `all`, `staff`, `parents`, `students`, `class:N`,
  `section:N`. Class/section paths walk through SIS students → linked
  parents (with `can_receive_notifications=True`).
- Endpoints:
  - `/v1/school-admin/communication/templates` GET + PUT (per-tenant).
  - `/v1/school-admin/communication/announcements` GET / POST (publish
    fans out instantly).
  - `/v1/school-admin/communication/outbox` for the delivery debug view.
  - `/v1/announcements` (any auth user) — own school's notice board.
  - `/v1/messages` (POST/GET inbox/sent) + `POST /{id}/read`.
  - `/v1/notifications` now reads the persisted `Notification` table
    (replacing Phase 10's stub) + `POST /{id}/read` + `POST /read-all`.
- Default templates seeded per tenant (`leave.decided`,
  `announcement.posted`, `fee.collected`).
- Hook: `decide_leave` (Phase 8) now fires `notify("leave.decided", ...)`
  to the parent that applied — best-effort so a comms hiccup never
  blocks the school admin's decision.

School Admin React
- New `/communication` page with **Announcements / Templates / Outbox**
  tabs. Announcements: pick audience (incl. class/section), publish
  with a flash showing "Notified N users". Templates: per-language
  subject + body editing with a channel chip-row. Outbox: per-status
  filter table with channel + address + status pill.

Flutter
- `NotificationsRepository` upgraded: int ids, real `read_at` field,
  `markRead(id)` + `markAllRead()` plumbing; new `AnnouncementsRepository`.
- Notifications page now shows pinned/recent announcements at the top,
  per-row tap to mark read, "Mark all read" button, read state styling
  via the dark/light theme outline.

Tests: 97 passing (7 new). Default templates seeded, announcement to
parents fans out + parent sees in their notifications, section-scoped
announcement targets only linked parents, leave decision triggers a
parent notification with the right title, direct messages round-trip
between two users, outbox correctly queues SMS rows when the template
includes the channel, mark-all-read clears the unread count.

## Phase 11 deliverables (shipped)

Live Razorpay integration, UPI QR generation, PDF receipt rendering, and
SMS/email reminders deferred — they need real keys + Phase 12's
communication pipes. The data path is fully wired: the online payment
flow is signature-verified end-to-end against a stub gateway, receipts
return JSON ready for Phase 16's PDF renderer, and reminder triggers
will reuse the Phase 10 notifications endpoint.

Backend
- Schema: `FeeCategory`, `FeeStructure`, `FeeInvoice`, `FeePayment`,
  `FeeDiscount` with the right indexes and uniques. Migration
  `99ff6b1ec51b`.
- `/v1/school-admin/fees` (gated to school staff for reads, admins +
  accountant for mutations):
  - Categories CRUD.
  - Structures CRUD with a `(class, category, period)` unique guard.
  - `POST /structures/{id}/generate` materialises invoices for every
    active student in the class. Auto-applies a sibling discount
    (configurable %) when the student belongs to a sibling group, plus
    any active explicit discount. Idempotent: re-running for the same
    period returns `created=0` and skips duplicates.
  - Discounts CRUD (`sibling / scholarship / staff_ward / manual`).
  - `GET /students/{id}` rolls up invoices + total due / paid / overdue
    counts and self-heals invoice status (paid > partial > overdue >
    pending precedence).
  - `POST /collect` records cash / UPI / card / bank transfer / cheque
    payments by accountants; rejects overpayment.
  - `GET /payments/{id}/receipt` returns the receipt JSON Phase 16's
    PDF renderer will consume.
  - `GET /reports/collection` (date-windowed totals + daily / by-method
    / by-category breakdowns) and `GET /reports/defaulters` (current
    overdue ranked by amount).
- Online payment stub (Razorpay-style):
  - `POST /v1/parent/payments/initiate` validates the parent-link, mints
    an `order_id`, persists a pending payment row.
  - `POST /v1/parent/payments/confirm` verifies an HMAC-SHA256 signature
    against the stored secret, marks payment SUCCESS, and credits the
    invoice.
  - `GET /v1/parent/children/{id}/fees` returns the same `StudentFeeView`
    parent-link guarded.
- Phase 8 `ChildDashboard.fee_due_amount` now actually computes from open
  invoices, so the parent dashboard tile is real.

School Admin React
- `/fees` page with **Categories / Structures / Collection / Reports**
  tabs. Structures tab can generate invoices for a date range with a
  configurable sibling discount %. Collection tab picks a student,
  shows their invoices with status pills, lets the accountant collect
  any amount with a method. Reports tab shows total collected /
  pending / overdue tiles plus a defaulter table.

Flutter
- The parent dashboard's stats grid now uses the real `feeDueAmount` and
  `todayAttendance` fields from the backend dashboard payload, with the
  fee tile coloured saffron when there's a balance and teal when clear.

Tests: 90 passing (8 new). Category + structure CRUD with duplicate
rejection, invoice generation with sibling discount math (10% of 1000
= 100, total 900), idempotent re-generation, full payment + partial +
overpay rejection paths, online HMAC signature flow with the right
secret, collection summary totals, defaulter list correctness, parent
dashboard fee_due_amount math (10% sibling on 750 = 675), parent
cannot view another kid's fees.

## Phase 10 deliverables (shipped)

Push notifications via Firebase + bio-auth + on-device performance work
deferred — they need native config that's better handled when an Android
project is set up for shipping. The data path the FCM client will hit
already exists (`/v1/notifications`).

Backend
- New `/v1/notifications` endpoint that returns a real, role-aware list
  (parents see decisions on leaves they applied for; school staff see
  pending leaves in the queue). The Phase 12 SMS/push delivery will
  reuse the same payload shape.

Flutter (school_erp_mobile/jaikalki)
- **Multi-language** scaffolding (`AppLanguage` + `AppStrings` for
  English / Hindi / Marathi). Every user-facing string in login,
  dashboard, settings, onboarding, notifications goes through it.
- **SettingsCubit** persists language + theme + onboarded flag in a
  Hive box.
- **Dark mode** — `JaikalkiBrand.darkTheme()` (indigo surfaces, saffron
  accent retained). MaterialApp respects `themeMode` from SettingsCubit.
- **Splash** at `/` routes to `/onboarding` on first launch, otherwise
  `/login` or `/home` based on auth state.
- **Onboarding** carousel (3 slides) seals the Hive `onboarded` flag
  before navigating away.
- **HomeShell** with `NavigationBar` (Home / Notifications / Settings)
  using `IndexedStack` for state preservation.
- **Notifications page** hits `/v1/notifications`, with empty state and
  pull-to-refresh.
- **Settings page** with language chips, theme chips, sign-out, about.
- **Offline cache** — `OfflineCache` over Hive; `ChildrenCubit` now
  warm-boots from cache before the network refresh, so the parent
  dashboard renders instantly even on a flaky connection.
- **Global error bus** — Dio `ErrorInterceptor` pipes failures into
  `ErrorBus`, surfaced as snackbars by `GlobalErrorListener` wrapping
  the entire MaterialApp tree.
- Login redirects to the new `/home` path; dashboard drops its own
  Scaffold/AppBar (HomeShell handles them).
- Widget test boots Hive in a temp dir, settings cubit, and confirms
  the splash → onboarding routing happens on first launch.

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
