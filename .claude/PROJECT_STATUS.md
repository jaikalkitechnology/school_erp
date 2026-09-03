# Jaikalki School ERP — Project Status

**Completed & pending across the whole project.**
Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
Apps: `backend` · `school_admin_web` · `super_admin_web` · `mobile/jaikalki`

## Summary

| ✅ Done | 🔶 Partial | ⏳ Pending | Overall |
|:------:|:---------:|:---------:|:-------:|
| 96 | 13 | 30 | **~78% complete** |

`139 tracked items · Done 69% · Partial 9% · Pending 22%`

**Legend** — ✅ **DONE** built & working · 🔶 **PARTIAL** works, has gaps · ⏳ **PENDING** not started · **🆕** shipped this work session

---

## 🧱 Platform & infrastructure — 6/6 done

| Task | Status | Detail |
|------|--------|--------|
| Multi-tenant core | ✅ DONE | TenantBase auto-filter, subdomain-first resolution, tenant-scoped sessions |
| FastAPI + async SQLAlchemy + Alembic + MySQL | ✅ DONE | Migrations + boot-time safety nets |
| JWT auth (access + refresh rotation) | ✅ DONE | Bearer + tenant header |
| Notification pipeline | ✅ DONE | in-app / push (FCM) / SMS / email fan-out via templates |
| File uploads service | ✅ DONE | Tenant-scoped, authed download |
| RBAC catalogue + role seeding | ✅ DONE | Re-seeded at boot; granted_admin_pages backfill |

## 🔐 Authentication & roles — 4 done · 1 partial · 3 pending

| Task | Status | Detail |
|------|--------|--------|
| Password login | ✅ DONE | All roles |
| Google Sign-In (web + Android) | ✅ DONE | JWKS verify, subdomain-first, invite-only. Needs deploy + Google Cloud config |
| Role-scoped sidebar / access | ✅ DONE | Librarian-only view, granted pages |
| Mobile role → shell routing | ✅ DONE 🆕 | student→Student, teacher/hod/management routed correctly |
| Password reset via OTP | 🔶 PARTIAL | Verify end-to-end on prod SMS gateway |
| Role × platform login gate | ⏳ PENDING | Was reverted; re-implement if wanted |
| Email-conflict policy on Google login | ⏳ PENDING | Confirm merge/reject rules with product |
| iOS Google Sign-In | ⏳ PENDING | Deferred — iOS OAuth client + URL scheme |

## 🖥️ Admin panel — modules (`school_admin_web`)

| Module | Status | Detail |
|--------|--------|--------|
| Dashboard | ✅ DONE | KPIs |
| School setup / Org | ✅ DONE | Classes, sections, subjects, houses; validation |
| Student management | ✅ DONE | Admit / edit / list, photo, validation; aadhaar 12-digit ⏳ |
| Staff / Users & credentials | ✅ DONE | HOD + Receptionist roles, "Bus Staff" rename; phone/email validation ⏳ |
| Academic + timetable | ✅ DONE | Timetable builder depth / substitution polish ⏳ |
| Exams + grade scales + report cards | ✅ DONE | Roster marks, results, PDF cards |
| Fee management | 🔶 PARTIAL | Works; sub-nav tabs not split into deep-link routes |
| Communication (SMS/Email/Push/Circulars) | 🔶 PARTIAL | Works; sub-nav points to one page |
| Library (20+ pages, full CRUD) | 🔶 PARTIAL | Books/copies/issue/return/fines/reservations done; Shelves + Settings localStorage, Import/Export stub, Audit synthesised, Barcode text-only ⏳ |
| Transport (8 tabs) | ✅ DONE | Fleet, Routes, Students, Live map, Live trip, Billing, History, Logs (fuel+maintenance) |
| Hostel | ✅ DONE | Rooms, allocations |
| Finance / Accounts | ✅ DONE | Vendors, expenses; FK + validation |
| Payroll / HR | ✅ DONE | Salary structures, payslips; payslip staff-picker ⏳ |
| Inventory & assets | ✅ DONE | Items, movements |
| Admissions | ✅ DONE | Inquiries pipeline (admin only) |
| Visitor management | ✅ DONE | Visitor log |
| Health / Infirmary | ✅ DONE | Health records |
| Certificates + ID cards | ✅ DONE | Templates, issue; student-picker on issue ⏳ |
| Discipline | ✅ DONE | Incident register |
| Notice board | ✅ DONE | Audience-targeted |
| Alumni | ✅ DONE | Registry |
| Sports & clubs | ✅ DONE | Houses, events |
| Campus management | ✅ DONE | Facilities |
| Subscription + Settings | ✅ DONE | Plan, branding, config |
| Reports | 🔶 PARTIAL | Standard reports; custom builder + scheduled email ⏳ |
| Mobile-friendly responsive layout | ✅ DONE | Drawer + hamburger, every panel |
| Org-chart sidebar hierarchy | ✅ DONE | Grouped nav |
| Form validation (phone/email/GST/number bounds) | ✅ DONE | Vendors, campus, inventory, library, students; Users phone+email + date-order guards ⏳ |

## 🛡️ Super admin (`super_admin_web`)

| Task | Status | Detail |
|------|--------|--------|
| 9-item sidebar nav | ✅ DONE 🆕 | Dashboard, Organizations, Plans, Billing, Staff, Reports, Announcements, Audit Logs, Settings |
| Dashboard | ✅ DONE | Platform overview |
| Organizations (tenant list + detail) | 🔶 PARTIAL | List + detail; full CRUD (create/suspend/cancel/limits) ⏳ |
| Onboarding wizard | 🔶 PARTIAL | Wizard exists; seed RBAC/first-admin/branding ⏳ |
| Audit log | ✅ DONE | Per-tenant; cross-tenant global viewer ⏳ |
| Plans management | ⏳ PENDING | View only; create/edit + feature flags |
| Billing / invoicing | ⏳ PENDING | View only; invoice generation, dunning |
| Staff page | ⏳ PENDING | Placeholder |
| Reports | ⏳ PENDING | Placeholder (route added) |
| Announcements | ⏳ PENDING | Placeholder (route added) |
| Settings | ⏳ PENDING | Placeholder |
| Impersonation ("log in as") | ⏳ PENDING | Scoped audited token |
| Form validation | ⏳ PENDING | Reuse operations _crud rules |

## 👨‍👩‍👧 Mobile — Parent (HomeShell · 5 tabs)

| Feature | Status | Detail |
|---------|--------|--------|
| Home dashboard + child switcher | ✅ DONE | Fees due, today's attendance, siblings |
| Attendance (+ by-subject, class avg) | ✅ DONE | |
| Homework (view, submit, attachments, grades) | ✅ DONE | No-section fallback fixed 🆕 |
| Result cards / Profile / Calendar | ✅ DONE | |
| Transport (route, driver, live tracking) | ✅ DONE | |
| Library / Directory / Messages / Notices | ✅ DONE | |
| Health / Discipline / Certificates / Sports | ✅ DONE | |
| Apply for leave | ✅ DONE 🆕 | Pick child, dates, reason + status history |
| Fee payment via gateway (Razorpay) | ⏳ PENDING | Needs Razorpay keys + order/verify endpoint |
| Admissions status view | ⏳ PENDING | If parent applied (needs parent-facing endpoint) |
| Offline caching (new ops pages) | 🔶 PARTIAL | Core cached; new pages ⏳ |

## 🎓 Mobile — Student (StudentShell · 4 tabs) 🆕

| Feature | Status | Detail |
|---------|--------|--------|
| Dedicated shell + /student self API | ✅ DONE 🆕 | Resolves own record via Student.user_id |
| Home dashboard | ✅ DONE 🆕 | Own attendance, homework, fees, documents |
| Attendance | ✅ DONE 🆕 | |
| Homework (view + submit) | ✅ DONE 🆕 | Text answer; attachments ⏳ |
| Timetable | ✅ DONE 🆕 | Weekly grid |
| Attendance by subject | ✅ DONE 🆕 | Per-subject % bars |
| Profile / Result cards | ✅ DONE 🆕 | |
| Library / Notices / Notifications / Settings | ✅ DONE 🆕 | Reused tenant-wide pages |
| Homework attachments on submit | ⏳ PENDING | Text-only today |

## 👩‍🏫 Mobile — Teacher (TeacherShell · 3 tabs)

| Feature | Status | Detail |
|---------|--------|--------|
| Today (self check-in) + Classes | ✅ DONE | |
| Take attendance | ✅ DONE | Online; offline-first + sync ⏳ |
| Homework create + grade | ✅ DONE | Submissions, marks, feedback |
| Enter exam marks | ✅ DONE 🆕 | Pick exam → paper → roster → bulk save |
| Exam + weekly timetable | ✅ DONE | |
| Behaviour notes / Chat | ✅ DONE | |
| Leave approvals + my leaves | ✅ DONE | |
| Notice board / Payslips / Sports / ID card | ✅ DONE | |
| Offline-first attendance | ⏳ PENDING | Larger infra |

## 🚌 Mobile — Bus staff (TransportShell · Bus + More)

| Feature | Status | Detail |
|---------|--------|--------|
| Transport shell + driver profile | ✅ DONE | |
| Route map | ✅ DONE | Stops + polyline |
| Students + navigate to pickup | ✅ DONE 🆕 | Turn-by-turn directions to pickup coords |
| Boarding scan + Notices | ✅ DONE | |
| Fuel / expense log entry | ⏳ PENDING | Backend exists in admin Logs tab — expose in driver app |
| Driver leave / unavailability | ⏳ PENDING | New |

## 🧪 Backend — validation & data model — 3 done · 4 pending

| Task | Status | Detail |
|------|--------|--------|
| Operations crash-proof coerce + guards | ✅ DONE | Enum/length/negative, friendly 400s, FK translation |
| Typed leave decide · SIS emails · fee amount > 0 | ✅ DONE | |
| Parent homework no-section fallback | ✅ DONE 🆕 | Falls back to class sections |
| SIS/teacher phone format | ⏳ PENDING | Bare Optional[str] |
| Aadhaar 12-digit validation | ⏳ PENDING | |
| max_length caps on free-text columns | ⏳ PENDING | address, remarks, religion… |
| Exam-marks bounds in Pydantic | ⏳ PENDING | Defense-in-depth |

## 🚀 Deployment / release — do first (all pending)

| Task | Status | Detail |
|------|--------|--------|
| Run Alembic migrations on prod | ⏳ PENDING | phase28 operations + google_sub |
| Redeploy backend | ⏳ PENDING | student API, homework fix, exam-marks, bus coords are server-side |
| Rebuild admin + super-admin web | ⏳ PENDING | `npm run build` → deploy dist/, hard-refresh |
| Rebuild mobile APK | ⏳ PENDING | New StudentShell, leave, exam-marks, google_sign_in plugin |
| Google Cloud console config | ⏳ PENDING | JS origins per subdomain, Android SHA-1, consent screen |

---

**How to read this.** Statuses reflect the code on branch `claude/analyze-school-erp-Kk7Z4`.
**Done** = built and working in code; **Partial** = usable with a named gap; **Pending** = not started.
Items tagged **🆕** were built in the latest work session. The five deployment items are the only
thing between the current code and a live release — everything marked Done is written but must be
deployed to run in production. Counts are indicative of tracked scope, not a line-by-line audit.
