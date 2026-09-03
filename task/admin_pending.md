# 🖥️ Admin Panel — Pending

Branch: `claude/analyze-school-erp-Kk7Z4` · Updated: 2026-09-03
App: `school_erp_school_admin_web`

Legend — ⏳ not started · 🔶 partial (works, has a gap)

> Nearly the whole admin_pending list is now **DONE** — see `admin_complete.md`:
> validation, pickers, backend phone/aadhaar/max_length, Fee/Communication
> deep-link routes, and every Library server-table item (shelves, settings,
> audit log, import, barcode, inventory verification).
>
> What remains are three **large features** that need dedicated design +
> new infrastructure (a report-query engine, a background scheduler + SMTP,
> file-upload models). They are intentionally NOT stubbed — each deserves its
> own focused, testable build rather than a blind half-implementation.

---

## Reports & depth (large — need infrastructure)

| Task | Status | What it needs |
|------|:------:|---------------|
| Reports: **custom report builder** | ⏳ | A query-builder engine (pick entity, columns, filters, grouping) + saved-report storage. Multi-day feature. |
| Reports: **scheduled email delivery** | ⏳ | A background scheduler (cron/worker) + SMTP/email service + per-report schedule config. New infra. |
| Timetable builder **depth / substitution UI** | 🔶 | Base timetable works; needs conflict detection, teacher-availability, and a substitute-assignment flow. |
| Report cards: **portfolio (project uploads, achievements)** | ⏳ | New upload model + per-student portfolio store + UI. (The grade-scheme editor is already built — Exams → Grade scale.) |

---

## Suggested order when picking these up
1. **Report cards portfolio** — most self-contained: one upload model + a tab.
2. **Custom report builder** — high value; start read-only over existing data.
3. **Scheduled email** — only after an email/worker service exists.
4. **Timetable substitution** — depends on availability data.
