# 📱 Mobile App — Pending

Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
App: `school_erp_mobile/jaikalki`

Legend — ⏳ not started · 🔶 partial (works, has a gap) · 🔴 blocked (needs your input)

---

## 👨‍👩‍👧 Parent

| Feature | Status | What's needed |
|---------|:------:|---------------|
| Fee payment via gateway (Razorpay) | 🔴 | Razorpay account + API key id/secret; backend order-create + signature-verify endpoint; enable `razorpay_flutter` (commented out in pubspec) |
| Admissions status view (if parent applied) | ⏳ | Parent-facing endpoint matching AdmissionInquiry by phone/email + a mobile page. Note: applicants usually have no login pre-enrolment |
| Offline caching for the new ops pages | 🔶 | Core screens cached; health/discipline/certificates/sports/leave not yet |

## 🎓 Student

| Feature | Status | What's needed |
|---------|:------:|---------------|
| Homework attachments on submit | ⏳ | Currently text-only; add photo/PDF picker like the parent flow |

## 👩‍🏫 Teacher

| Feature | Status | What's needed |
|---------|:------:|---------------|
| Offline-first attendance + sync | ⏳ | Local queue + background sync (larger infra) |
| Homework grading polish (bulk / quick-grade) | 🔶 | Grading works one-by-one; add bulk actions |

## 🚌 Bus staff

| Feature | Status | What's needed |
|---------|:------:|---------------|
| Fuel / expense log entry | ⏳ | Data model already exists (admin Transport → Logs); expose entry in the driver app |
| Driver leave / unavailability marking | ⏳ | New endpoint + mobile screen |

## 🔐 Auth (affects app)

| Feature | Status | What's needed |
|---------|:------:|---------------|
| Role × platform login gate | ⏳ | Was reverted; block parents/students from admin web & back-office from app, if wanted |
| iOS Google Sign-In | ⏳ | iOS OAuth client + URL scheme (Android + web already done) |
| Password reset via OTP | 🔶 | Verify end-to-end on prod SMS gateway |

---

## 🚀 Deployment — required for ANY app change to go live

| Task | Status | Detail |
|------|:------:|--------|
| Redeploy backend | ⏳ | Student API, homework fix, exam-marks, bus coords are server-side |
| Rebuild mobile APK | ⏳ | `flutter pub get && flutter clean && flutter build apk` — new StudentShell, leave, exam-marks, `google_sign_in` native plugin |
