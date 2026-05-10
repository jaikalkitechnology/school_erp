# Jaikalki School ERP - Multi-Tenant SaaS

**Product:** Multi-Tenant School ERP for Jaikalki Technology
**Project Path:** `C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp`
**Database:** `db_school_jaikalki` (MySQL, password: Love1718)
**File Storage:** Local (school_backend/uploads/)
**Total Duration:** ~10 months | ~1,500 hours
**API Cost:** ~$150-200 (Claude Code)

---

## 🎯 Quick Overview

A **complete SaaS School ERP** that Jaikalki sells to multiple schools. Each school gets:
- Their own subdomain (e.g., `dpsschool.jaikalki.com`)
- Custom branding (logo, colors)
- Isolated data (multi-tenant)
- Mobile app for everyone
- Web admin for Super Admin (Jaikalki) AND School Admin (Per School)

---

## 🏗️ Architecture

```
React Admin Web (TWO LEVELS)
├── Super Admin (Jaikalki) - Manages all schools
└── School Admin (Per School) - Manages their school
                ↓
                ↓ HTTPS
                ↓
        FastAPI Backend (Multi-Tenant)
        + Local File Storage (uploads/)
                ↓
                ↓
        MySQL + Redis
                ↑
                ↑ HTTPS
                ↑
Flutter Mobile App (Everyone)
- School Admin    - Class Teacher
- Principal       - Subject Teacher
- Coordinator     - Parent (multi-child)
- Accountant      - Student
- Librarian       - Office Staff
- Transport Mgr   - Hostel Warden
```

**File Storage:** All files stored locally in `school_backend/uploads/tenant_X/` (NO S3/MinIO)

---

## 👥 13 User Roles

### Web Admin (React) - Two Levels
1. **Super Admin** - Jaikalki product owner (manages all schools)
2. **School Admin** ⭐ - Per-school admin (full school control + approvals + overall view)

### Mobile App (Flutter)
3. **School Admin** (Mobile) - Quick approvals on-the-go
4. **Principal** - Educational head
5. **Vice Principal** (Optional)
6. **Head Teacher / Coordinator** - Department head
7. **Class Teacher** - Class mentor
8. **Subject Teacher** - Subject specialist
9. **Accountant** - Fee/financial
10. **Librarian** - Library
11. **Transport Manager** - Bus operations
12. **Hostel Warden** - For boarding schools
13. **Office Staff** - Reception
14. **Parent** ⭐ - Multi-child access
15. **Student** - Senior classes (9th+)

---

## 📁 File Storage Strategy (Local)

**No S3/MinIO** - Everything stored in backend directory:

```
school_backend/uploads/
├── tenant_1/                    # School 1
│   ├── students/photos/
│   ├── students/documents/
│   ├── teachers/photos/
│   ├── exams/question_papers/
│   ├── homework/submissions/
│   ├── fees/receipts/
│   ├── reports/report_cards/
│   ├── library/book_covers/
│   └── branding/logo.png
├── tenant_2/                    # School 2
│   └── (same structure)
└── ...
```

**Features:**
- Per-tenant folder isolation
- Image auto-optimization (Pillow)
- Storage quota per subscription plan
- Authenticated file serving
- Easy backup with tar/rsync

---

## 📋 Documentation Files

Place all in:
```
C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp\erp_structure\
```

| File | Purpose |
|------|---------|
| **SchoolERP_Architecture.md** | Main architecture spec |
| **PHASE_00_Foundation.md** | Project setup |
| **PHASES_01_to_22.md** | All other phases |
| **README.md** | This file |

---

## 🚀 Phase Roadmap

| Phase | Module | Days | Hours |
|-------|--------|------|-------|
| 0 | Foundation (3 projects) | 4 | 30 |
| 1 | Multi-Tenant Architecture | 7 | 50 |
| 2 | Auth & RBAC (13 roles) | 10 | 70 |
| 3 | Super Admin (School Onboarding) | 10 | 70 |
| 4 | School Admin Foundation | 7 | 60 |
| 5 | Academic Setup | 7 | 50 |
| 6 | Student Information System | 10 | 80 |
| 7 | Teacher Management | 7 | 60 |
| 8 | Parent Module (Multi-Child) ⭐ | 10 | 75 |
| 9 | Attendance Management | 7 | 60 |
| 10 | Mobile App Polish | 10 | 80 |
| 11 | Fee Management | 14 | 95 |
| 12 | Communication System | 7 | 60 |
| 13 | Time Table & Substitution | 7 | 60 |
| 14 | Homework & Assignment | 7 | 60 |
| 15 | Examination System | 14 | 90 |
| 16 | Report Cards | 7 | 50 |
| 17 | Library Management | 5 | 40 |
| 18 | Transport (with GPS) | 10 | 70 |
| 19 | Hostel Management | 7 | 50 |
| 20 | Reports & Analytics | 7 | 60 |
| 21 | Subscription & Billing | 7 | 50 |
| 22 | Final Testing & Deployment | 10 | 70 |

**Total: ~1,440 hours core**

---

## 💰 SaaS Pricing Strategy

### Tiers

| Plan | Price | Students | Features |
|------|-------|----------|----------|
| Basic | ₹15/student/month | Up to 200 | Core only |
| Standard | ₹25/student/month | 200-1000 | + Exams, Reports, Transport |
| Premium | ₹40/student/month | 1000+ | All features |
| Enterprise | Custom | Unlimited | Custom integrations |

### Revenue Projection

**100 schools × 500 avg students × ₹25 = ₹12,50,000/month**
- Operating cost: ~₹63,000
- **Net profit: ~₹11,87,000/month = ₹1.42 Cr/year**

---

## 🎯 MVP Scope (First 4 months)

**Phases 0-10 = Launch-ready MVP:**
- Multi-tenant working
- All 13 roles authenticated
- Super Admin can onboard schools
- School can manage students/teachers/classes
- Parents can use multi-child app
- Attendance + basic communication
- Simple fee payment
- Mobile app polished

**MVP Cost:** ~$70-80 (Claude Code API)

---

## 🚀 Getting Started

### Step 1: Setup Folder

```bash
cd C:\Users\Shyamveer\PycharmProjects
mkdir jaikalki_school_erp
cd jaikalki_school_erp
mkdir erp_structure
```

### Step 2: Place MD Files

Download all .md files and place in `erp_structure\`

### Step 3: Run Claude Code

```bash
claude

# Phase 0
"Read erp_structure/SchoolERP_Architecture.md and 
erp_structure/PHASE_00_Foundation.md.

Implement Phase 0 for Jaikalki School ERP.
Database: db_school_jaikalki
Password: Love1718
Create 3 projects: school_backend, school_admin_web, school_mobile.

Apply Jaikalki branding (Brown #3D2817 + Gold #F4B71F)."
```

### Step 4: Test Phase 0

```bash
# Backend
cd school_backend
docker-compose up -d
uvicorn app.main:app --reload
# http://localhost:8000/health

# React
cd school_admin_web
npm run dev
# http://localhost:5173

# Flutter
cd school_mobile
flutter run -d chrome
```

### Step 5: Continue with Next Phases

```bash
# Phase 1
"Read erp_structure/PHASES_01_to_22.md (Phase 1 section).
Implement Phase 1 (Multi-Tenant Architecture)."

# Phase 2
"Implement Phase 2 (Authentication & RBAC) with 13 roles."

# ...and so on
```

---

## ⭐ Critical Features

### 1. Multi-Tenant Isolation
- Every table has `tenant_id`
- Subdomain detection
- Strict row-level security
- Test: Tenant A NEVER sees Tenant B's data

### 2. Multi-Child Parent
- Single login, multiple children
- Top-of-screen child switcher
- Per-child notifications
- Smooth UX

### 3. Mobile-First (95% on mobile)
- All daily tasks on mobile
- Offline mode
- Push notifications
- Multi-language

### 4. White-Labeling
- School logo
- School colors
- Custom subdomain
- Future: custom mobile app

---

## 🎨 Branding (Jaikalki)

Default theme (overridable per school):
- Primary: `#3D2817` (Deep Brown)
- Accent: `#F4B71F` (Gold)
- Background: `#FAFAF7` (Warm White)

---

## 🔐 Security Highlights

- JWT with tenant_id in claims
- Multi-tenant strict isolation
- DPDP Act 2023 compliance
- Parental consent for minors
- Audit logs for sensitive actions
- Encrypted sensitive data
- Bus tracking with privacy
- Photo upload consent

---

## 📊 Success Metrics

### For Jaikalki
- Number of schools (target: 100 in Year 1)
- MRR growth
- Churn rate (<5%)
- NPS score (>50)

### For Schools
- Parent app adoption (>80%)
- Daily active users (>60%)
- Fee collection rate (>95%)
- Communication delivery (>98%)

---

## 🎯 Competitive Advantages

vs Existing School ERPs (Eduvate, Fedena, MyClassboard):

1. **Modern Tech** - Flutter app vs old hybrid apps
2. **Multi-Child UX** - Best in class
3. **Indian-First** - Hindi/Marathi/regional
4. **Affordable** - 30-50% cheaper
5. **Faster Onboarding** - 7 days vs 30 days
6. **Better Mobile** - True mobile-first
7. **WhatsApp Integration** - Indian families prefer
8. **Offline-First** - Tier 2/3 cities
9. **GPS Bus Tracking** - Parent peace of mind
10. **AI-Free** - Practical features only

---

## 📞 Support During Development

If Claude Code gets stuck:
1. Be specific: "Fix tenant isolation in students endpoint"
2. Show errors: paste exact errors
3. Reference files: "Look at app/models/tenant.py"
4. Restart conversation if context full

Common issues:
- Tenant_id missing: Always include in queries
- Foreign keys: MySQL strict, check tenant match
- Subdomain detection: Test with Postman first

---

## ✅ Final Checklist

After Phase 22:
- [ ] All 13 roles authenticated
- [ ] Multi-tenant strictly isolated
- [ ] 5 sample schools tested
- [ ] 100+ test users
- [ ] Mobile app on Android + iOS + Web
- [ ] React admin deployed
- [ ] Razorpay integrated
- [ ] SMS/Email working
- [ ] WhatsApp Business API
- [ ] GPS bus tracking
- [ ] Reports generating
- [ ] Backups automated
- [ ] SSL certificates
- [ ] Documentation complete
- [ ] Team trained

🎉 **Ready to onboard schools!**

---

**Document Version:** 1.0
**Created:** April 2026
**Total Phases:** 23 (Phase 0 to 22)
**Product:** Jaikalki School ERP SaaS
