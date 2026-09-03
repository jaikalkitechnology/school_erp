# 📱 Mobile App — Completed

Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
App: `school_erp_mobile/jaikalki` · 🆕 = built in the latest work session

> Note: features marked ✅ are complete **in code**; they go live only after the mobile
> APK is rebuilt and the backend is redeployed (see `task/app_pending.md` → Deployment).

---

## 👨‍👩‍👧 Parent (HomeShell · 5 tabs)

| Feature | Status |
|---------|:------:|
| Home dashboard + child switcher (fees due, today's attendance, siblings) | ✅ |
| Attendance (history + by-subject + class average) | ✅ |
| Homework — view, submit, photo/PDF attachments, grades & feedback | ✅ |
| Homework "no section" fix (shows class homework) | ✅ 🆕 |
| Result cards | ✅ |
| Student profile | ✅ |
| Calendar (events + holidays) | ✅ |
| Transport (route, driver, live tracking) | ✅ |
| Library catalog | ✅ |
| Contact directory (teachers) | ✅ |
| Messages / chat | ✅ |
| Notice board | ✅ |
| Health records | ✅ |
| Discipline register | ✅ |
| Certificates | ✅ |
| Sports & clubs | ✅ |
| **Apply for leave** (pick child, dates, reason + status history) | ✅ 🆕 |
| Notifications | ✅ |
| Settings (language toggle) | ✅ |
| Google Sign-In | ✅ |

## 🎓 Student (StudentShell · 4 tabs) — new shell 🆕

| Feature | Status |
|---------|:------:|
| Dedicated shell + `/v1/student` self API (own data via Student.user_id) | ✅ 🆕 |
| Home dashboard (own attendance, homework due, fees, documents) | ✅ 🆕 |
| Attendance | ✅ 🆕 |
| Homework (view + submit text answer) | ✅ 🆕 |
| Timetable (weekly grid) | ✅ 🆕 |
| Attendance by subject (per-subject % bars) | ✅ 🆕 |
| My profile | ✅ 🆕 |
| Result cards | ✅ 🆕 |
| Library / Notice board / Notifications / Settings | ✅ 🆕 |
| Sign out | ✅ 🆕 |

## 👩‍🏫 Teacher (TeacherShell · 3 tabs)

| Feature | Status |
|---------|:------:|
| Today (self check-in "mark me present") | ✅ |
| Classes / sections + student drill-down | ✅ |
| Take attendance | ✅ |
| Homework — create (with attachments), list, view submissions, grade | ✅ |
| **Enter exam marks** (pick exam → paper → roster → bulk save) | ✅ 🆕 |
| Exam timetable | ✅ |
| Weekly timetable | ✅ |
| Behaviour notes | ✅ |
| Chat (admins & parents) | ✅ |
| Leave approvals (decide student leave) | ✅ |
| My leaves (apply + track) | ✅ |
| Calendar | ✅ |
| Notice board | ✅ |
| My payslips | ✅ |
| Sports & clubs | ✅ |
| Teacher ID card | ✅ |
| Role routing (teacher / hod / management → correct shell) | ✅ 🆕 |

## 🚌 Bus staff (TransportShell · Bus + More)

| Feature | Status |
|---------|:------:|
| Transport shell + driver profile | ✅ |
| Route map (stops + polyline) | ✅ |
| Students list + **navigate to pickup** (turn-by-turn directions) | ✅ 🆕 |
| Boarding scan | ✅ |
| Notices | ✅ |

## 🔐 Cross-cutting

| Feature | Status |
|---------|:------:|
| Multi-child support (ChildrenCubit) | ✅ |
| Push notifications (FCM) | ✅ |
| Multi-language strings (SettingsCubit) | ✅ |
| Google Sign-In (parent/staff) | ✅ |
