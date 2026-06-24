# Jaikalki School ERP - Multi-Tenant SaaS Architecture

**Product Owner:** Jaikalki Technology Pvt Ltd
**Product Type:** Multi-Tenant SaaS for Schools
**Target Customers:** Pre-school to K-12 (Any board: CBSE/ICSE/State/IB)
**Project Path:** `C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp`
**Database:** `db_school_jaikalki` (MySQL)
**Stack:** FastAPI + React (Admin Web) + Flutter (Mobile/Web/iOS) + MySQL + Redis + Local File Storage

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Multi-Tenant Architecture](#2-multi-tenant-architecture)
3. [Role & Permission System](#3-role--permission-system)
4. [Database Design](#4-database-design)
5. [Backend Architecture](#5-backend-architecture)
6. [React Admin Web (Super Admin)](#6-react-admin-web-super-admin)
7. [Flutter Mobile App (Everyone Else)](#7-flutter-mobile-app-everyone-else)
8. [Core Modules](#8-core-modules)
9. [Subscription & Billing](#9-subscription--billing)
10. [Communication System](#10-communication-system)
11. [Mobile-First Features](#11-mobile-first-features)
12. [Security & Compliance](#12-security--compliance)
13. [Deployment Strategy](#13-deployment-strategy)
14. [Phased Roadmap](#14-phased-roadmap)

---

## 1. Product Overview

### Vision

A complete digital ecosystem for schools that connects:
- **Administration** (Principal, Admin)
- **Educators** (Teachers, Coordinators)
- **Parents** (with multi-child access)
- **Students** (Senior classes)
- **Operations** (Librarian, Transport, Accountant)

All on a **single mobile app** + React admin panel for Super Admin.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  JAIKALKI SCHOOL ERP - MULTI-TENANT SAAS               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  React Admin Web (Two Levels)                           │
│  ├─ Super Admin (Jaikalki) - Manages all schools        │
│  └─ School Admin (Per School) - Manages their school    │
│                                                          │
│  Features for both:                                     │
│  - Full CRUD operations                                 │
│  - Approval workflows                                   │
│  - Overall analytics & reports                          │
│  - Bulk operations                                      │
│  Tech: React + TypeScript + Tailwind + shadcn/ui        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Flutter Mobile App (Everyone Including School Admin)   │
│  Single app, role-based UI:                             │
│  ├─ School Admin (mobile - quick approvals on-the-go)  │
│  ├─ Principal                                           │
│  ├─ Head Teacher / Coordinator                          │
│  ├─ Class Teacher                                       │
│  ├─ Subject Teacher                                     │
│  ├─ Parent (multi-child)                                │
│  ├─ Student (senior classes)                            │
│  ├─ Accountant                                          │
│  ├─ Librarian                                           │
│  ├─ Transport Manager                                   │
│  └─ Other staff                                         │
 │  Platforms: Android + iOS + Web                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Multi-Tenant Aware)                   │
│  ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Auth   │ │ Tenant Mgmt │ │  RBAC    │ │ Services │ │
│  └─────────┘ └─────────────┘ └──────────┘ └──────────┘ │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Local File Storage (uploads/ directory)         │  │
│  │  Per-tenant folder isolation                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
   ┌────▼────┐                    ┌────▼─────┐
   │  MySQL  │                    │  Redis   │
   │ (with   │                    │  (cache) │
   │ tenant_ │                    │          │
   │ id)     │                    │          │
   └─────────┘                    └──────────┘

   Files stored in:
   school_backend/uploads/
   ├── tenant_1/
   │   ├── students/
   │   ├── teachers/
   │   ├── documents/
   │   └── photos/
   ├── tenant_2/
   └── ...
```

### Key Differentiators

1. **Single Mobile App** - Student, Parent, Teacher, Principal all use same app
2. **Multi-Child Parent Login** - Switch between siblings easily
3. **Indian Languages** - Hindi, Marathi, Tamil, etc.
4. **Offline-First** - Works in Tier 2/3 cities
5. **Affordable** - SaaS pricing makes it accessible
6. **Quick Onboarding** - Schools live in 7 days
7. **WhatsApp Integration** - For parent communication
8. **GPS Bus Tracking** - Parents track school bus
9. **Multi-Tenant Secure** - Strong data isolation

---

## 2. Multi-Tenant Architecture

### Tenant Strategy: Shared Database + Row-Level Isolation

**Why this approach:**
- ✅ Cost effective (one DB instance for many schools)
- ✅ Faster onboarding (no DB provisioning)
- ✅ Easier maintenance (one schema to manage)
- ✅ Better resource utilization
- ⚠️ Requires strict tenant_id enforcement

### Tenant ID Strategy

Every school = One tenant. Every table has `tenant_id` column.

```sql
-- Every business table has this
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,  -- ⭐ KEY FIELD
    -- other columns...
    INDEX idx_tenant (tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

### Tenant Isolation Methods

#### 1. Database Level
```sql
-- Composite indexes always include tenant_id
CREATE INDEX idx_tenant_class ON students(tenant_id, class_id);

-- Foreign keys check tenant_id matches
-- (enforced at application level)
```

#### 2. Application Level (FastAPI)

```python
# Middleware extracts tenant_id from JWT
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    user = get_current_user(request)
    request.state.tenant_id = user.tenant_id

# Base query class auto-filters by tenant
class TenantQuery(Query):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.model, 'tenant_id'):
            self.filter(tenant_id=current_tenant_id())
```

#### 3. URL Level (Subdomain Routing)

Each school gets:
- `dpsschool.jaikalki.com`
- `nps.jaikalki.com`
- `vidyaschool.jaikalki.com`

```python
# Subdomain detection
@app.middleware("http")
async def subdomain_middleware(request: Request, call_next):
    host = request.headers.get('host')
    subdomain = host.split('.')[0]
    tenant = await get_tenant_by_subdomain(subdomain)
    request.state.tenant = tenant
```

### Tenant Management

```sql
CREATE TABLE tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_name VARCHAR(200) NOT NULL,
    school_code VARCHAR(20) UNIQUE NOT NULL,
    subdomain VARCHAR(50) UNIQUE NOT NULL,

    -- School details
    affiliation_board ENUM('CBSE','ICSE','STATE','IB','CAMBRIDGE','OTHER'),
    school_type ENUM('PRESCHOOL','PRIMARY','SECONDARY','HIGHER_SECONDARY','K12'),
    medium ENUM('ENGLISH','HINDI','MARATHI','TAMIL','TELUGU','KANNADA','OTHER'),
    is_boarding BOOLEAN DEFAULT FALSE,

    -- Contact
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    phone VARCHAR(20),
    email VARCHAR(100),
    website VARCHAR(200),

    -- Branding
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#3D2817',
    secondary_color VARCHAR(7) DEFAULT '#F4B71F',

    -- Subscription
    plan_id INT,
    subscription_start DATE,
    subscription_end DATE,
    student_limit INT DEFAULT 500,
    teacher_limit INT DEFAULT 50,

    -- Status
    status ENUM('TRIAL','ACTIVE','SUSPENDED','EXPIRED','CANCELLED') DEFAULT 'TRIAL',
    is_active BOOLEAN DEFAULT TRUE,

    -- Configuration
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    academic_year_start_month INT DEFAULT 4,  -- April start
    grading_system ENUM('PERCENTAGE','GPA','LETTER','GRADE_5','GRADE_10'),

    -- Modules enabled
    modules_enabled JSON,  -- {"hostel": true, "transport": true, ...}

    -- Audit
    onboarded_by INT,
    onboarded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 3. Role & Permission System

### 13 Distinct Roles

```
LEVEL 10: Super Admin (Jaikalki Owner)
   ↓ [Manages All Schools]

LEVEL 9: School Admin (Per School)
   ↓ [School-wide Management]

LEVEL 8: Principal
   ↓ [Educational Head]

LEVEL 7: Vice Principal (Optional)
   ↓ [Deputy to Principal]

LEVEL 6: Head Teacher / Coordinator
   ↓ [Department/Section Head]

LEVEL 5: Class Teacher
   ↓ [Class Mentor + Subject Teacher]

LEVEL 5: Subject Teacher
   ↓ [Subject Specialist]

LEVEL 4: Accountant
   ↓ [Financial Operations]

LEVEL 4: Librarian
   ↓ [Library Management]

LEVEL 4: Transport Manager
   ↓ [Bus & Routes]

LEVEL 4: Hostel Warden (if boarding)
   ↓ [Hostel Operations]

LEVEL 3: Office Staff / Receptionist
   ↓ [Front Desk]

LEVEL 2: Parent (Multi-Child Access)
   ↓ [Track children]

LEVEL 1: Student (Senior Classes - 9th+)
   ↓ [Self-Service]
```

### Detailed Role Capabilities

#### 🔐 Super Admin (Jaikalki) - Web Only
**Purpose:** Manages the entire SaaS platform across all schools

**Powers:**
- Onboard new schools (full setup wizard)
- Suspend/activate schools
- Subscription & billing management
- View all schools dashboard
- Cross-school analytics
- System-wide announcements
- Platform configuration
- Database management
- Audit logs (all schools)
- Customer support tickets
- White-label customization
- Master templates (curriculum, fee, etc.)

#### 👨‍💼 School Admin - Web (Primary) + Mobile (Secondary) ⭐
**Purpose:** School's IT/Office administrator with FULL control

**Web Access (React Admin) - Primary Interface:**
- Complete dashboard with all school metrics
- Full CRUD on all entities:
  - Students (admission, transfer, withdrawal)
  - Teachers (onboarding, subjects, classes)
  - Parents (account creation, multi-child mapping)
  - Classes & Sections
  - Subjects
  - Holidays
  - Time Tables
- **Approval workflows:**
  - Admission approvals
  - Document verification
  - Fee waiver requests
  - Teacher leaves (extended)
  - Discount approvals
  - Refund approvals
  - Transfer requests
- **Overall views:**
  - All students dashboard
  - All teachers performance
  - Class-wise analytics
  - Department-wise reports
  - Financial overview
  - Attendance trends
  - Communication logs
- **Bulk operations:**
  - Bulk student import (Excel)
  - Bulk SMS/Email
  - Bulk fee operations
  - Bulk ID card generation
  - Bulk certificate generation
- **Configuration:**
  - School settings
  - Module enable/disable
  - Branding (logo, colors)
  - Email/SMS templates
  - Report card templates
  - Fee structure setup
- **Reports:**
  - Generate any report
  - Custom report builder
  - Export to Excel/PDF
  - Scheduled reports
- **Audit:**
  - View all activities
  - User activity logs
  - Data change history

**Mobile Access (Flutter App) - Quick Actions:**
- Daily dashboard summary
- Quick approvals (swipe actions):
  - Leave approvals
  - Admission approvals
  - Fee waivers
- Real-time notifications
- Quick stats viewing
- Emergency announcements
- View pending tasks
- Approve from anywhere
- View ongoing operations
- Communication with staff/parents
- Quick reports

**Why Both Web + Mobile:**
- Web: Heavy operations, data entry, bulk actions, detailed reports
- Mobile: Quick approvals, on-the-go monitoring, emergency response

#### 👨‍🏫 Principal - Mobile + Web
**Purpose:** Educational head, decision maker

**Powers:**
- School-wide dashboard
- All teachers & staff overview
- Academic performance metrics
- Approve major decisions:
  - Extended teacher leaves
  - Fee waivers/discounts
  - Disciplinary actions
  - Admission approvals
- Class-wise pass percentages
- Teacher performance reviews
- Parent grievance escalations
- Annual planning
- Mass communications
- View all reports
- Override permissions when needed
- Inspection reports

#### 👩‍💼 Vice Principal (Optional)
**Powers:** Same as Principal but with restrictions on:
- Can't approve fee waivers above ₹X
- Can't terminate teachers
- Reports to Principal

#### 👥 Head Teacher / Coordinator
**Purpose:** Department or section head (e.g., Primary Section, Math Department)

**Powers (within department):**
- View department teachers only
- Approve teacher leaves (1st level)
- Subject allocation
- Lesson plan review
- Substitute teacher arrangement
- Department meetings
- Mid-term teacher reviews
- Student counseling escalations
- Parent meetings coordination
- Curriculum updates
- Department reports

#### 📚 Class Teacher
**Purpose:** Class mentor + Subject teacher

**Class-Related Powers:**
- Daily class attendance
- Class discipline tracking
- Parent-teacher communication for class
- Class performance overview
- Field trip organization
- Class fund management
- Student behavior notes
- Assembly conduct
- House management

**Subject-Related Powers:** (Same as Subject Teacher below)

#### 📖 Subject Teacher
**Purpose:** Teaches specific subjects

**Powers:**
- Subject-wise attendance
- Lesson plan creation
- Homework assignment
- Online tests/quizzes
- Marks entry
- Comments on student progress
- Parent communication
- Leave application
- View timetable
- Substitution acceptance
- Resource sharing
- Question bank creation
- Result entry
- Behavioral notes
- Parent meeting requests

#### 💰 Accountant
**Powers:**
- Fee collection
- Receipt generation
- Defaulter list management
- Fee reminders
- Refund processing
- Salary processing
- Vendor payments
- Financial reports
- Tax calculations
- Bank reconciliation
- Petty cash
- Audit support

#### 📚 Librarian
**Powers:**
- Book catalog management
- Issue/return tracking
- Defaulter management
- New book entry
- Reservations
- Reading recommendations
- Library reports
- Inventory audit

#### 🚌 Transport Manager
**Powers:**
- Route management
- Driver assignment
- Vehicle tracking
- Maintenance scheduling
- Fuel consumption
- Student route assignment
- Pickup/drop verification
- Emergency response
- Parent communication

#### 🏠 Hostel Warden (Boarding Schools)
**Powers:**
- Room allocation
- Roommate matching
- Mess management
- Hostel attendance
- Visitor log
- Disciplinary records
- Health monitoring
- Leave applications
- Maintenance requests

#### 🪑 Office Staff / Receptionist
**Powers:**
- Visitor management
- Inquiry handling
- Document collection
- Parent appointment booking
- Phone call logs
- Application receiving
- Basic info dispensing
- Emergency contact relay

#### 👨‍👩‍👧‍👦 Parent (Multi-Child Critical Feature)
**Powers (per child):**
- Switch between children (top-of-screen selector)
- View attendance per child
- View grades/report cards
- Homework tracker
- Fee payment online
- Receipt download
- View timetable
- Exam schedule
- Holiday calendar
- Communicate with teachers
- Apply leave for child
- Track school bus location
- View school events
- Photo gallery (events)
- Notice board
- Library books issued
- Medical records
- Behavior reports
- Online PTM booking
- Lunch menu (if applicable)
- Permission slips (digital sign)
- Document downloads (TC, Bonafide)

#### 👨‍🎓 Student (Class 9th and Above)
**Powers:**
- View own attendance
- View own grades
- Homework submission
- Take online tests
- View timetable
- Library books
- Notice board
- Study material download
- Doubt asking to teachers
- View achievements
- Class announcements

### Permission Matrix Sample

| Permission | Super Admin | School Admin | Principal | HT | Teacher | Parent | Student |
|------------|-------------|--------------|-----------|----|---------|---------| --------|
| `tenant.create` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `school.config` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `student.create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `student.view.all` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `student.view.dept` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `student.view.class` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `student.view.own` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `attendance.mark` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `homework.create` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `homework.submit` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `marks.enter` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `marks.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `fee.collect` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `fee.pay` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `report.school` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 4. Database Design

### Core Tables Structure

```sql
-- ============== TENANT MANAGEMENT ==============
tenants                 # All schools (described above)
subscription_plans      # Pricing tiers
subscriptions          # Active subscriptions
billing_invoices       # Monthly bills
payment_history        # Tenant payments

-- ============== AUTHENTICATION ==============
users                  # All users across all roles (with tenant_id)
user_sessions          # Active sessions
roles                  # Role definitions
permissions            # Permission catalog
role_permissions       # Role-permission mapping
user_roles             # User-role mapping (multi-role support)
parent_children        # Parent-multiple-child mapping

-- ============== SCHOOL STRUCTURE ==============
academic_years         # 2024-25, 2025-26, etc.
classes                # Nursery, LKG, 1st, 2nd, ..., 12th
sections               # A, B, C, D
class_sections         # Mapping (1-A, 1-B, etc.)
subjects               # Math, English, Hindi, Science...
class_subjects         # Subjects taught in each class
houses                 # Red, Blue, Green, Yellow (school houses)

-- ============== STUDENT INFORMATION ==============
students               # Complete student profile
student_admissions     # Admission process tracking
student_documents      # Birth cert, photos, etc.
student_medical_info   # Allergies, medications
student_previous_school # Transfer info
student_siblings       # Sibling discount tracking
student_house_assignment # House membership

-- ============== TEACHER INFORMATION ==============
teachers               # Teacher profile
teacher_qualifications # Education details
teacher_subjects       # Subjects they teach
teacher_classes        # Classes they handle
teacher_class_teacher  # Class teacher assignment

-- ============== PARENT INFORMATION ==============
parents                # Parent profiles
parent_address         # Multiple addresses
parent_emergency_contact

-- ============== ATTENDANCE ==============
student_attendance     # Daily attendance
attendance_settings    # School-wise rules
student_leaves         # Leave requests by parents
teacher_attendance     # Teacher attendance
biometric_logs         # If biometric integrated

-- ============== ACADEMIC ==============
timetables            # Class-wise schedules
timetable_periods     # Period definitions
substitutions         # Teacher substitutions
holidays              # School calendar

-- ============== EXAMINATIONS ==============
exam_types            # Quarterly, Half-yearly, etc.
exams                 # Exam schedules
exam_subjects         # Subjects in each exam
hall_tickets          # Generated tickets
seat_arrangements     # Hall arrangements
question_papers       # Question bank
marks                 # Subject-wise marks
grades                # Calculated grades
report_cards          # Generated report cards
report_card_templates # Customizable

-- ============== HOMEWORK & ASSIGNMENTS ==============
homeworks             # Homework assignments
homework_attachments  # Files attached
homework_submissions  # Student submissions
submission_grades     # Teacher grading
online_tests          # MCQ tests
test_questions        # Test question bank
test_attempts         # Student attempts
test_results          # Auto-evaluated

-- ============== FEE MANAGEMENT ==============
fee_categories        # Tuition, Transport, Lab, etc.
fee_structures        # Class-wise fee structure
fee_installments      # Monthly/Quarterly schedule
student_fees          # Student-wise fee records
fee_payments          # Payment transactions
fee_receipts          # Generated receipts
fee_discounts         # Sibling, Scholarship, etc.
fee_late_charges      # Penalty configuration
fee_reminders         # Auto-reminder log

-- ============== COMMUNICATION ==============
notifications         # In-app notifications
notification_settings # Per-user preferences
sms_logs             # SMS sent log
email_logs           # Email sent log
announcements        # School-wide announcements
notice_board         # Notice posting
messages             # Internal messaging
message_threads      # Conversation threads
ptm_meetings         # PTM scheduling
ptm_slots           # Available slots

-- ============== TRANSPORT ==============
buses                 # Vehicle details
routes                # Route definitions
route_stops           # Pickup/drop points
bus_drivers           # Driver info
student_transport     # Student-route mapping
bus_tracking          # Live GPS data
bus_attendance        # Boarding/alighting

-- ============== LIBRARY ==============
books                 # Book catalog
book_categories       # Categorization
book_issues           # Issue records
book_returns          # Return records
book_reservations     # Hold requests
library_fines         # Late return fines

-- ============== HOSTEL ==============
hostels               # Hostel buildings
rooms                 # Rooms in hostels
room_allocations      # Student-room mapping
hostel_attendance     # Daily attendance
mess_menus            # Daily menu
visitor_logs          # Hostel visitors

-- ============== EVENTS & ACTIVITIES ==============
events                # School events
event_participants    # Registration
sports_events         # Sports tournaments
sports_teams          # Team formation
competitions          # Inter-school
achievements          # Student achievements
photo_gallery         # Event photos
gallery_albums        # Album organization

-- ============== HEALTH ==============
health_checkups       # Annual checkups
medical_visits        # Doctor visits in school
vaccinations          # Vaccination records
allergies             # Per-student allergies

-- ============== DISCIPLINE ==============
discipline_incidents  # Behavioral incidents
warning_letters       # Issued warnings
counseling_sessions   # Counselor records

-- ============== ALUMNI ==============
alumni                # Past students
alumni_career         # Career tracking
alumni_events         # Reunion events

-- ============== STAFF (Non-Teaching) ==============
staff                 # Non-teaching staff
staff_attendance      # Their attendance
staff_salary          # Salary info

-- ============== INVENTORY ==============
inventory_items       # All school items
inventory_categories  # Type
inventory_issues      # Issue/receive
inventory_audit       # Stock audits

-- ============== AUDIT & LOGS ==============
audit_logs            # All system actions
login_history         # Login tracking
data_changes          # Track data modifications

-- ============== SETTINGS ==============
school_settings       # Per-school config
academic_settings     # Grading, etc.
notification_templates # Reusable templates
```

---

## 5. Backend Architecture

### File Storage Strategy (Local Filesystem)

**No S3/MinIO** - All files stored in FastAPI backend directory with strict tenant isolation.

#### Directory Structure

```
school_backend/
├── app/                          # Application code
├── uploads/                      # ⭐ ALL FILES HERE
│   ├── tenant_1/                 # School 1 (DPS School)
│   │   ├── students/
│   │   │   ├── photos/
│   │   │   │   └── student_{id}.jpg
│   │   │   ├── documents/
│   │   │   │   ├── birth_cert/
│   │   │   │   ├── aadhaar/
│   │   │   │   ├── tc/
│   │   │   │   └── other/
│   │   │   └── id_cards/
│   │   ├── teachers/
│   │   │   ├── photos/
│   │   │   ├── documents/
│   │   │   │   ├── qualification/
│   │   │   │   ├── experience/
│   │   │   │   └── other/
│   │   │   └── id_cards/
│   │   ├── parents/
│   │   │   └── documents/
│   │   ├── exams/
│   │   │   ├── question_papers/
│   │   │   ├── answer_sheets/
│   │   │   └── hall_tickets/
│   │   ├── homework/
│   │   │   ├── assignments/
│   │   │   └── submissions/
│   │   ├── fees/
│   │   │   └── receipts/
│   │   ├── reports/
│   │   │   ├── report_cards/
│   │   │   └── certificates/
│   │   ├── library/
│   │   │   └── book_covers/
│   │   ├── transport/
│   │   │   └── vehicle_docs/
│   │   ├── events/
│   │   │   └── photos/
│   │   ├── communication/
│   │   │   └── attachments/
│   │   ├── branding/
│   │   │   ├── logo.png
│   │   │   └── theme/
│   │   └── temp/                 # Temporary uploads
│   │
│   ├── tenant_2/                 # School 2
│   │   └── (same structure)
│   │
│   └── tenant_3/                 # School 3
│       └── (same structure)
│
├── alembic/
├── tests/
├── requirements.txt
└── docker-compose.yml
```

#### File Upload Service

```python
# app/services/file_service.py
import os
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from uuid import uuid4
from PIL import Image

class LocalFileStorageService:
    """Manages file storage in backend directory with tenant isolation"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def get_tenant_path(self, tenant_id: int, category: str = None) -> Path:
        """Get path for specific tenant + category"""
        path = self.base_path / f"tenant_{tenant_id}"
        if category:
            path = path / category
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    async def upload_file(
        self,
        file: UploadFile,
        tenant_id: int,
        category: str,
        subcategory: str = None,
        entity_id: int = None,
        max_size_mb: int = 10
    ) -> dict:
        """
        Upload file with tenant isolation
        
        Args:
            file: UploadFile from FastAPI
            tenant_id: Current tenant
            category: students/teachers/exams/etc
            subcategory: photos/documents/etc
            entity_id: Optional entity reference
            max_size_mb: Max file size
        
        Returns:
            dict with file_path, file_url, file_size, etc.
        """
        # Validate file size
        contents = await file.read()
        size_mb = len(contents) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise HTTPException(
                status_code=413, 
                detail=f"File size {size_mb:.1f}MB exceeds limit of {max_size_mb}MB"
            )
        
        # Validate file type
        allowed_extensions = self._get_allowed_extensions(category)
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {allowed_extensions}"
            )
        
        # Generate unique filename
        unique_name = f"{uuid4().hex}{file_ext}"
        if entity_id:
            unique_name = f"{entity_id}_{unique_name}"
        
        # Construct path
        path_parts = [str(tenant_id), category]
        if subcategory:
            path_parts.append(subcategory)
        
        full_dir = self.base_path / Path(*path_parts)
        full_dir.mkdir(parents=True, exist_ok=True)
        
        full_path = full_dir / unique_name
        
        # Save file
        with open(full_path, 'wb') as f:
            f.write(contents)
        
        # Optimize images
        if file_ext in ['.jpg', '.jpeg', '.png']:
            self._optimize_image(full_path)
        
        # Generate relative URL
        relative_path = full_path.relative_to(self.base_path)
        file_url = f"/files/{relative_path}".replace('\\', '/')
        
        return {
            'file_name': unique_name,
            'original_name': file.filename,
            'file_path': str(full_path),
            'file_url': file_url,
            'file_size': len(contents),
            'mime_type': file.content_type,
            'category': category,
            'subcategory': subcategory,
            'tenant_id': tenant_id,
            'entity_id': entity_id,
        }
    
    def _optimize_image(self, file_path: Path, max_width: int = 1920):
        """Compress images for storage efficiency"""
        try:
            with Image.open(file_path) as img:
                # Resize if too large
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Save with compression
                img.save(file_path, optimize=True, quality=85)
        except Exception as e:
            print(f"Image optimization failed: {e}")
    
    def _get_allowed_extensions(self, category: str) -> list:
        """Get allowed file extensions per category"""
        rules = {
            'students/photos': ['.jpg', '.jpeg', '.png'],
            'teachers/photos': ['.jpg', '.jpeg', '.png'],
            'students/documents': ['.pdf', '.jpg', '.jpeg', '.png'],
            'teachers/documents': ['.pdf', '.jpg', '.jpeg', '.png'],
            'exams/question_papers': ['.pdf', '.docx'],
            'homework/assignments': ['.pdf', '.docx', '.jpg', '.png'],
            'homework/submissions': ['.pdf', '.docx', '.jpg', '.png', '.zip'],
            'fees/receipts': ['.pdf'],
            'reports/report_cards': ['.pdf'],
            'branding': ['.png', '.svg', '.jpg'],
            'events/photos': ['.jpg', '.jpeg', '.png'],
            'communication/attachments': ['.pdf', '.docx', '.jpg', '.png'],
        }
        
        # Default - common safe types
        default = ['.pdf', '.jpg', '.jpeg', '.png', '.docx']
        
        # Try specific match first
        for key, extensions in rules.items():
            if category.startswith(key.split('/')[0]):
                return extensions
        
        return default
    
    def delete_file(self, file_path: str, tenant_id: int) -> bool:
        """Delete file with tenant verification"""
        full_path = self.base_path / file_path
        
        # Security: Verify file belongs to tenant
        if not str(full_path).startswith(str(self.base_path / f"tenant_{tenant_id}")):
            raise HTTPException(
                status_code=403,
                detail="Cannot delete file from different tenant"
            )
        
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def get_tenant_storage_size(self, tenant_id: int) -> dict:
        """Calculate storage used by tenant"""
        tenant_path = self.base_path / f"tenant_{tenant_id}"
        if not tenant_path.exists():
            return {'size_mb': 0, 'file_count': 0}
        
        total_size = 0
        file_count = 0
        for file in tenant_path.rglob('*'):
            if file.is_file():
                total_size += file.stat().st_size
                file_count += 1
        
        return {
            'size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
        }


# Initialize service
file_storage = LocalFileStorageService(base_path="uploads")
```

#### File Serving Endpoint

```python
# app/api/v1/files.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

@router.get("/files/{tenant_id}/{path:path}")
async def serve_file(
    tenant_id: int,
    path: str,
    current_user = Depends(get_current_user),
):
    """
    Serve uploaded file with tenant isolation check
    """
    # Verify user belongs to tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Construct safe path
    base_path = Path("uploads") / f"tenant_{tenant_id}"
    file_path = base_path / path
    
    # Security: Prevent path traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="Invalid path")
    except:
        raise HTTPException(status_code=403, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


@router.post("/upload")
async def upload_file(
    file: UploadFile,
    category: str,
    subcategory: str = None,
    entity_id: int = None,
    current_user = Depends(get_current_user),
):
    """Upload file with automatic tenant assignment"""
    result = await file_storage.upload_file(
        file=file,
        tenant_id=current_user.tenant_id,
        category=category,
        subcategory=subcategory,
        entity_id=entity_id,
    )
    return result


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user = Depends(get_current_user),
):
    """Delete file (with tenant verification)"""
    # Get file record from DB
    file_record = await get_file_by_id(file_id)
    
    # Verify ownership
    if file_record.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403)
    
    # Delete physical file
    file_storage.delete_file(file_record.file_path, current_user.tenant_id)
    
    # Delete DB record
    await delete_file_record(file_id)
    
    return {"deleted": True}
```

#### Database File Tracking

```sql
CREATE TABLE uploaded_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    
    -- File info
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    file_path VARCHAR(500) NOT NULL,
    file_url VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),
    
    -- Categorization
    category VARCHAR(50) NOT NULL,    -- students, teachers, exams, etc
    subcategory VARCHAR(50),          -- photos, documents, etc
    entity_type VARCHAR(50),          -- student, teacher, exam, etc
    entity_id INT,                    -- Reference to entity
    
    -- Metadata
    uploaded_by INT,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Audit
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP NULL,
    
    INDEX idx_tenant (tenant_id),
    INDEX idx_category (tenant_id, category),
    INDEX idx_entity (tenant_id, entity_type, entity_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Backup Strategy

Since files are local, **regular backups are critical**:

```bash
# Daily backup script (Linux/Windows)
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/files"

# Compress uploads directory
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" /path/to/school_backend/uploads

# Keep last 30 days
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +30 -delete

# Optional: Sync to remote (rsync, rclone)
rsync -avz $BACKUP_DIR remote:/backup-server/
```

#### Storage Limits per Tenant

```python
TENANT_STORAGE_LIMITS = {
    'BASIC': 5 * 1024,      # 5 GB in MB
    'STANDARD': 25 * 1024,  # 25 GB
    'PREMIUM': 100 * 1024,  # 100 GB
    'ENTERPRISE': -1,       # Unlimited
}

async def check_storage_quota(tenant_id: int):
    """Check if tenant exceeded storage limit"""
    tenant = await get_tenant(tenant_id)
    plan = tenant.subscription_plan
    
    usage = file_storage.get_tenant_storage_size(tenant_id)
    limit = TENANT_STORAGE_LIMITS[plan.code]
    
    if limit > 0 and usage['size_mb'] > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Storage limit exceeded ({usage['size_mb']:.0f}MB / {limit}MB)"
        )
```

### Folder Structure

```
school_backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── core/
│   │   ├── tenant.py            # ⭐ Multi-tenancy
│   │   ├── security.py
│   │   ├── permissions.py
│   │   ├── middleware.py
│   │   └── file_storage.py      # ⭐ Local file storage
│   │
│   ├── models/
│   ├── schemas/
│   ├── api/
│   │   ├── v1/                  # Regular APIs
│   │   │   ├── auth.py
│   │   │   ├── students.py
│   │   │   ├── files.py         # ⭐ File upload/serve
│   │   │   └── ...
│   │   └── admin/               # Super Admin APIs
│   │
│   ├── services/
│   │   ├── file_service.py      # ⭐ File operations
│   │   └── ...
│   ├── tasks/
│   └── utils/
│
├── uploads/                     # ⭐ ALL UPLOADED FILES
│   ├── tenant_1/
│   │   ├── students/
│   │   ├── teachers/
│   │   └── ...
│   ├── tenant_2/
│   └── ...
│
├── alembic/
├── tests/
├── requirements.txt
└── docker-compose.yml
```

---

## 6. React Admin Web (Super Admin + School Admin)

### Two-Level Access

The React web app serves **TWO admin levels**:

```
┌────────────────────────────────────────────┐
│  Login → Detect Role → Route Accordingly   │
└────────────────────────────────────────────┘
                  ↓
        ┌─────────┴──────────┐
        ↓                    ↓
┌──────────────┐    ┌──────────────────┐
│ Super Admin  │    │  School Admin    │
│ (Jaikalki)   │    │  (Per School)    │
│              │    │                  │
│ Manages:     │    │ Manages:         │
│ - All schools│    │ - One school only│
│ - Tenants    │    │ - All entities   │
│ - Billing    │    │ - All operations │
│ - System     │    │ - Approvals      │
└──────────────┘    └──────────────────┘
```

### Folder Structure (Two Admin Levels)

```
school_admin_web/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   │
│   ├── lib/
│   │   ├── api/
│   │   ├── utils.ts
│   │   └── constants.ts
│   │
│   ├── components/
│   │   ├── ui/                        # shadcn components
│   │   ├── layouts/
│   │   │   ├── SuperAdminLayout.tsx   # For Jaikalki
│   │   │   ├── SchoolAdminLayout.tsx  # For school admin
│   │   │   └── SharedHeader.tsx
│   │   └── shared/
│   │       ├── DataTable.tsx
│   │       ├── ApprovalCard.tsx       # Reusable approval UI
│   │       ├── BulkActions.tsx
│   │       └── PermissionGate.tsx
│   │
│   ├── features/
│   │   ├── super-admin/                ⭐ SUPER ADMIN ONLY
│   │   │   ├── Dashboard.tsx
│   │   │   ├── tenants/
│   │   │   │   ├── TenantList.tsx
│   │   │   │   ├── OnboardSchool.tsx
│   │   │   │   └── TenantDetail.tsx
│   │   │   ├── subscriptions/
│   │   │   │   ├── PlanManagement.tsx
│   │   │   │   └── BillingHistory.tsx
│   │   │   ├── analytics/
│   │   │   │   └── PlatformAnalytics.tsx
│   │   │   └── system/
│   │   │       ├── DatabaseHealth.tsx
│   │   │       └── AuditLogs.tsx
│   │   │
│   │   ├── school-admin/               ⭐ SCHOOL ADMIN
│   │   │   ├── Dashboard.tsx           # Comprehensive dashboard
│   │   │   ├── students/
│   │   │   │   ├── StudentList.tsx
│   │   │   │   ├── StudentDetail.tsx
│   │   │   │   ├── AdmissionApprovals.tsx
│   │   │   │   ├── BulkImport.tsx
│   │   │   │   └── PromotionWizard.tsx
│   │   │   ├── teachers/
│   │   │   │   ├── TeacherList.tsx
│   │   │   │   ├── TeacherOnboarding.tsx
│   │   │   │   └── SubjectAllocation.tsx
│   │   │   ├── parents/
│   │   │   │   ├── ParentList.tsx
│   │   │   │   └── MultiChildMapping.tsx
│   │   │   ├── classes/
│   │   │   │   ├── ClassManagement.tsx
│   │   │   │   ├── SectionManagement.tsx
│   │   │   │   └── SubjectMaster.tsx
│   │   │   ├── timetable/
│   │   │   │   ├── TimetableBuilder.tsx
│   │   │   │   └── SubstitutionManager.tsx
│   │   │   ├── attendance/
│   │   │   │   ├── AttendanceOverview.tsx
│   │   │   │   ├── ClassWiseReport.tsx
│   │   │   │   └── DefaulterList.tsx
│   │   │   ├── examinations/
│   │   │   │   ├── ExamScheduling.tsx
│   │   │   │   ├── HallTickets.tsx
│   │   │   │   └── ResultsManagement.tsx
│   │   │   ├── fees/
│   │   │   │   ├── FeeStructure.tsx
│   │   │   │   ├── FeeCollection.tsx
│   │   │   │   ├── DefaulterManagement.tsx
│   │   │   │   └── DiscountApprovals.tsx
│   │   │   ├── communication/
│   │   │   │   ├── BulkMessaging.tsx
│   │   │   │   ├── NoticeBoard.tsx
│   │   │   │   └── Templates.tsx
│   │   │   ├── transport/
│   │   │   │   ├── RouteManagement.tsx
│   │   │   │   └── DriverManagement.tsx
│   │   │   ├── library/
│   │   │   │   └── BookCatalog.tsx
│   │   │   ├── approvals/                ⭐ KEY FEATURE
│   │   │   │   ├── ApprovalCenter.tsx    # All pending approvals
│   │   │   │   ├── LeaveApprovals.tsx
│   │   │   │   ├── AdmissionApprovals.tsx
│   │   │   │   ├── FeeWaiverApprovals.tsx
│   │   │   │   └── DocumentVerification.tsx
│   │   │   ├── reports/
│   │   │   │   ├── ReportBuilder.tsx
│   │   │   │   ├── ScheduledReports.tsx
│   │   │   │   └── ExportManager.tsx
│   │   │   ├── settings/
│   │   │   │   ├── SchoolSettings.tsx
│   │   │   │   ├── BrandingSettings.tsx
│   │   │   │   ├── ModuleSettings.tsx
│   │   │   │   └── EmailSmsTemplates.tsx
│   │   │   └── overview/                 ⭐ HIGH-LEVEL VIEWS
│   │   │       ├── SchoolOverview.tsx
│   │   │       ├── PerformanceOverview.tsx
│   │   │       ├── FinancialOverview.tsx
│   │   │       └── AttendanceOverview.tsx
│   │   │
│   │   └── shared/                     # Used by both
│   │       ├── auth/
│   │       ├── notifications/
│   │       └── profile/
│   │
│   ├── hooks/
│   ├── store/
│   │   ├── authStore.ts
│   │   ├── tenantStore.ts
│   │   └── appStore.ts
│   ├── types/
│   └── router/
│       └── routes.tsx                  # Role-based routing
```

### Role-Based Routing (Key Logic)

```tsx
// router/routes.tsx
const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/super-admin',
    element: (
      <ProtectedRoute requireRole="super_admin">
        <SuperAdminLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'dashboard', element: <SuperAdminDashboard /> },
      { path: 'tenants', element: <TenantList /> },
      { path: 'tenants/onboard', element: <OnboardSchool /> },
      // ... super admin routes
    ],
  },
  {
    path: '/school-admin',
    element: (
      <ProtectedRoute requireRole="school_admin">
        <SchoolAdminLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'dashboard', element: <SchoolAdminDashboard /> },
      { path: 'students', element: <StudentList /> },
      { path: 'teachers', element: <TeacherList /> },
      { path: 'approvals', element: <ApprovalCenter /> },
      // ... school admin routes
    ],
  },
]);

// On login, redirect based on role:
function LoginRedirect({ user }) {
  if (user.role === 'super_admin') return <Navigate to="/super-admin/dashboard" />;
  if (user.role === 'school_admin') return <Navigate to="/school-admin/dashboard" />;
  return <Navigate to="/unauthorized" />;
}
```

### School Admin Dashboard (Comprehensive)

```
┌────────────────────────────────────────────────────────────┐
│  🏫 [School Logo] DPS School - School Admin Console        │
│  📅 Today: Friday, 15 May 2026                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📊 QUICK STATS                                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Students │ │Teachers │ │Classes  │ │Pending  │          │
│  │  1,245  │ │   58    │ │  35     │ │  12 ⚠️  │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                            │
│  🎯 TODAY'S OPERATIONS                                     │
│  ✅ Attendance: 1,189 / 1,245 (95.5%) ✓                   │
│  💰 Fee Collected: ₹4,52,000 today                        │
│  📨 SMS Sent: 234 / 1000                                   │
│  🚌 Bus Status: All running on time                       │
│                                                            │
│  ⚠️ PENDING APPROVALS (12)                                 │
│  ┌──────────────────────────────────────┐                 │
│  │ • 5 Leave applications                │                 │
│  │ • 3 Fee waiver requests               │                 │
│  │ • 2 Admission approvals               │                 │
│  │ • 2 Document verifications            │                 │
│  └──────────────────────────────────────┘                 │
│  [View All Approvals →]                                    │
│                                                            │
│  📈 TRENDS (Last 7 Days)                                   │
│  [Attendance Chart]    [Fee Collection Chart]              │
│                                                            │
│  🚨 ALERTS                                                 │
│  • 8 students attendance < 75% (need parent meeting)      │
│  • 23 fee defaulters (>30 days)                           │
│  • 3 documents expiring this month                        │
│  • 2 teachers on extended leave                           │
│                                                            │
│  📋 RECENT ACTIVITIES                                      │
│  • Mr. Sharma added student "Aarav Patel" - 10 min ago    │
│  • Mrs. Verma marked attendance for Class 5A - 1 hr ago   │
│  • Fee receipt #4521 generated - 2 hrs ago                │
│                                                            │
└────────────────────────────────────────────────────────────┘

Sidebar Menu:
┌─────────────────────┐
│ 📊 Dashboard        │
│ 👨‍🎓 Students        │
│ 👨‍🏫 Teachers        │
│ 👨‍👩‍👧 Parents        │
│ 🏫 Classes          │
│ 📅 Time Table       │
│ ✓ Attendance        │
│ 📝 Examinations     │
│ 💰 Fee Management   │
│ 📚 Library          │
│ 🚌 Transport        │
│ 💬 Communication    │
│ 📨 Approvals (12)   │
│ 📊 Reports          │
│ ⚙️ Settings         │
└─────────────────────┘
```

### Approval Center (Critical Feature)

Centralized approval system for school admin:

```tsx
// features/school-admin/approvals/ApprovalCenter.tsx

Categories:
├── Leave Approvals (Teacher leaves > 3 days)
├── Admission Approvals (New student admissions)
├── Fee Waiver Requests
├── Discount Approvals (above threshold)
├── Document Verifications
├── Withdrawal/TC Requests
├── Refund Approvals
├── Bulk Operations Approval
└── Parent Grievances Escalated

UI Features:
- Tabs by category
- Quick approve/reject (swipe-like buttons)
- Bulk approve same type
- Add comments
- Reassign to other admin
- View attachments
- Approval history
- Auto-routing rules
```

### Bulk Operations

School Admin web has powerful bulk operations:

- **Bulk Student Import:**
  - Excel template download
  - Validation
  - Preview
  - Error report
  - Commit

- **Bulk Communication:**
  - Select students/parents/teachers
  - Choose channel (SMS/Email/WhatsApp/Push)
  - Use template or compose
  - Schedule send
  - Delivery report

- **Bulk Fee Operations:**
  - Generate fee for class
  - Apply discount to multiple
  - Send reminders to defaulters
  - Bulk receipt generation

- **Bulk Promotion:**
  - End of year promotion
  - Class change
  - Section change
  - Detain specific students

### Permission Differences

| Feature | Super Admin | School Admin |
|---------|-------------|--------------|
| Manage tenants | ✅ | ❌ |
| Onboard schools | ✅ | ❌ |
| Subscription billing | ✅ | ❌ |
| Cross-school analytics | ✅ | ❌ |
| Manage own school | ❌ | ✅ |
| Approve admissions | ❌ | ✅ |
| Generate reports | Cross-school | School only |
| Modify branding | ✅ | ⚠️ Limited |
| View audit logs | All schools | Own school only |

---

## 7. Flutter Mobile App (Everyone Else)

### Single App, Role-Based UI

The Flutter app intelligently shows different home screens and features based on logged-in user's role.

### App Structure

```
lib/
├── main.dart
├── core/
│   ├── routing/
│   │   └── role_based_router.dart  # ⭐ Critical
│   ├── theme/
│   ├── di/
│   └── network/
│
├── features/
│   ├── auth/                       # Universal
│   │   ├── login/
│   │   ├── biometric/
│   │   └── forgot_password/
│   │
│   ├── shared/                     # All roles use
│   │   ├── notifications/
│   │   ├── profile/
│   │   ├── messaging/
│   │   └── settings/
│   │
│   ├── super_admin/                # Super Admin (limited mobile)
│   │
│   ├── school_admin/               # School Admin
│   │   ├── dashboard/
│   │   ├── student_management/
│   │   ├── teacher_management/
│   │   ├── class_management/
│   │   └── reports/
│   │
│   ├── principal/                  # Principal
│   │   ├── dashboard/
│   │   ├── approvals/
│   │   ├── analytics/
│   │   └── grievances/
│   │
│   ├── coordinator/                # Head Teacher
│   │   ├── dashboard/
│   │   ├── department_view/
│   │   └── teacher_approvals/
│   │
│   ├── teacher/                    # Class + Subject Teacher
│   │   ├── dashboard/
│   │   ├── attendance/
│   │   ├── homework/
│   │   ├── tests/
│   │   ├── marks_entry/
│   │   ├── timetable/
│   │   └── communication/
│   │
│   ├── parent/                     # ⭐ Multi-child
│   │   ├── child_switcher/
│   │   ├── dashboard/
│   │   ├── attendance_view/
│   │   ├── grades_view/
│   │   ├── homework_view/
│   │   ├── fee_payment/
│   │   ├── bus_tracker/
│   │   ├── ptm_booking/
│   │   └── communication/
│   │
│   ├── student/                    # Senior students
│   │   ├── dashboard/
│   │   ├── homework_submit/
│   │   ├── tests_take/
│   │   ├── grades_view/
│   │   └── library/
│   │
│   ├── accountant/                 # Accountant
│   ├── librarian/                  # Librarian
│   ├── transport_manager/          # Transport
│   └── hostel_warden/              # Hostel
```

### Role Detection Flow

```dart
// On login success
class AuthBloc {
  Future<void> handleLoginSuccess(User user) async {
    // 1. Store user with role
    await storage.saveUser(user);

    // 2. Determine home route based on role
    final homeRoute = _getHomeRoute(user.role);

    // 3. Navigate to role-specific home
    GoRouter.of(context).go(homeRoute);
  }

  String _getHomeRoute(String role) {
    switch (role) {
      case 'school_admin':
        return '/admin/dashboard';
      case 'principal':
        return '/principal/dashboard';
      case 'coordinator':
        return '/coordinator/dashboard';
      case 'class_teacher':
      case 'subject_teacher':
        return '/teacher/dashboard';
      case 'parent':
        return '/parent/dashboard';
      case 'student':
        return '/student/dashboard';
      case 'accountant':
        return '/accountant/dashboard';
      case 'librarian':
        return '/librarian/dashboard';
      case 'transport_manager':
        return '/transport/dashboard';
      case 'hostel_warden':
        return '/hostel/dashboard';
      default:
        return '/unauthorized';
    }
  }
}
```

### Multi-Child Parent Feature (Critical)

```dart
class ParentDashboard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // ⭐ CHILD SWITCHER (always visible at top)
          ChildSwitcherWidget(
            children: parent.children,
            selectedChild: currentChild,
            onChildChange: (child) {
              context.read<ParentBloc>().selectChild(child);
            },
          ),

          // Selected child's dashboard
          Expanded(
            child: ChildDashboard(child: currentChild),
          ),
        ],
      ),
    );
  }
}

class ChildSwitcherWidget extends StatelessWidget {
  // Tab-style switcher with child photo + name + class
  // Easy switching between siblings
  // Shows alerts/notifications per child
}
```

### Sample Parent Dashboard

```
┌──────────────────────────────────┐
│  👨‍👩‍👧‍👦  Welcome, Mr. Sharma     │
├──────────────────────────────────┤
│  Select Child:                    │
│  ┌─────────┐  ┌─────────┐        │
│  │ 👦 Aarav│  │ 👧 Diya │        │
│  │ Class 5A│  │ Class 2B│        │
│  │ ●(1 new)│  │         │        │
│  └─────────┘  └─────────┘        │
├──────────────────────────────────┤
│  AARAV (Class 5A)                 │
│  ─────────────────                │
│  🎯 Today's Status:               │
│  ✅ Present                        │
│  📚 2 Homework Pending            │
│  💰 Fee Due: ₹15,000              │
│  🚌 Bus arrived: 7:45 AM          │
│                                   │
│  Quick Actions:                   │
│  [ Pay Fee ]  [ Apply Leave ]    │
│  [ View Bus ] [ Message Teacher] │
│                                   │
│  Recent:                          │
│  • Math test on Monday            │
│  • Sports day next week           │
│  • PTM scheduled tomorrow         │
└──────────────────────────────────┘
```

---

## 8. Core Modules

### Module Priorities (MVP First)

#### 🔴 MUST-HAVE (MVP - First 3 months)

1. **Authentication & RBAC**
   - Multi-role login
   - Biometric (mobile)
   - Forgot password
   - Multi-child parent

2. **Tenant Management**
   - School onboarding
   - Subscription
   - Branding

3. **Student Information System**
   - Admission
   - Profile management
   - Documents
   - Family info

4. **Class & Section Management**
   - Academic year
   - Class structure
   - Section assignment
   - Subject mapping

5. **Teacher Management**
   - Teacher onboarding
   - Subject allocation
   - Class teacher assignment

6. **Attendance**
   - Daily marking
   - Subject-wise (senior)
   - Auto SMS to parents
   - Reports

7. **Communication**
   - Notifications (push)
   - Internal messaging
   - SMS gateway
   - Email
   - Notice board

8. **Fee Management** (Basic)
   - Fee structure
   - Payment collection
   - Receipts
   - Defaulter list
   - Online payment

9. **Mobile App Polish**
   - Role-based dashboards
   - Offline mode basics
   - Multi-language (English + Hindi)

#### 🟠 PHASE 2 (Months 4-6)

10. **Time Table**
    - Auto-generation
    - Substitutions
    - Period management

11. **Examination**
    - Exam scheduling
    - Hall tickets
    - Marks entry
    - Online exams (MCQ)
    - Result analysis

12. **Report Cards**
    - Customizable templates
    - PDF generation
    - Comparison
    - Multi-board support

13. **Homework & Assignment**
    - Daily assignment
    - File upload
    - Submission tracking
    - Grading

14. **PTM (Parent-Teacher Meeting)**
    - Scheduling
    - Slot booking
    - Online PTM (video)
    - Notes

15. **Library Management**
    - Book catalog
    - Issue/return
    - Reservations
    - Fines

#### 🟢 PHASE 3 (Months 7-9)

16. **Transport Management**
    - Routes
    - GPS tracking
    - Driver app
    - Parent visibility

17. **Hostel Management** (Optional per school)
    - Room allocation
    - Mess
    - Visitor log

18. **Health Records**
    - Health card
    - Vaccinations
    - Medical visits

19. **Sports & Activities**
    - Events
    - Teams
    - Tournaments

20. **Discipline Management**
    - Incidents
    - Warnings
    - Counseling

21. **Reports & Analytics**
    - Custom report builder
    - Predictive analytics
    - Comparative reports

#### 🔵 PHASE 4 (Months 10-12)

22. **Online Classes Integration**
    - Zoom/Meet
    - Recorded classes
    - Doubt sessions

23. **Learning Management System (LMS)**
    - Video lectures
    - Interactive content
    - Self-learning

24. **Alumni Management**

25. **Inventory Management**

26. **Visitor Management**

27. **Lost & Found**

28. **Lunch/Canteen Management**

---

## 9. Subscription & Billing

### Pricing Tiers

#### 🥉 Basic Plan - ₹15/student/month
**For Pre-schools & Primary (up to 200 students)**
- Students: Up to 200
- Teachers: Up to 20
- Modules:
  - Authentication
  - Student management
  - Attendance
  - Basic fee
  - Communication (SMS limited)
  - Mobile app
- Storage: 5 GB
- Support: Email only

#### 🥈 Standard Plan - ₹25/student/month
**For Mid-size Schools (200-1000 students)**
- Everything in Basic +
- Time table
- Examinations
- Report cards
- Homework
- PTM
- Library (basic)
- Transport
- Storage: 25 GB
- SMS: 1000/month
- Support: Email + Chat

#### 🥇 Premium Plan - ₹40/student/month
**For Large Schools (1000+ students)**
- Everything in Standard +
- Hostel management
- Online classes integration
- Advanced analytics
- Custom reports
- LMS
- Alumni management
- White-label option
- Storage: Unlimited
- SMS: Unlimited
- Support: 24/7 dedicated
- Custom domain

#### 💎 Enterprise - Custom
**For chains, large institutions**
- Multi-campus
- Custom integrations
- Dedicated server
- SLA guarantees
- On-site training
- Dedicated account manager

### Billing Cycles

- Monthly
- Quarterly (5% discount)
- Annual (15% discount)
- Bi-annual (10% discount)

### Add-ons (Available on all plans)

- Extra SMS pack: ₹500/1000 SMS
- Extra storage: ₹500/10 GB
- Custom mobile app: ₹50,000 one-time
- Custom branding: ₹10,000 one-time
- Bus GPS devices: ₹3,000/device + ₹200/month/device

---

## 10. Communication System

### Multi-Channel Approach

```
                    NOTIFICATION ENGINE
                          ↓
        ┌────────┬────────┼────────┬────────┐
        │        │        │        │        │
   In-App   Push    SMS     Email  WhatsApp
   (Bell)   (FCM)  (Gate)         (Business)
```

### Notification Types & Channels

| Event | In-App | Push | SMS | Email | WhatsApp |
|-------|--------|------|-----|-------|----------|
| Student absent | ✅ | ✅ | ✅ | ❌ | ✅ |
| Homework posted | ✅ | ✅ | ❌ | ❌ | ❌ |
| Marks announced | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fee due | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fee paid | ✅ | ✅ | ❌ | ✅ | ❌ |
| Holiday declared | ✅ | ✅ | ✅ | ❌ | ✅ |
| PTM scheduled | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bus delay | ✅ | ✅ | ✅ | ❌ | ✅ |
| Emergency | ✅ | ✅ | ✅ | ✅ | ✅ |

### Smart Notifications

- Quiet hours (10 PM - 7 AM)
- Importance levels (Critical/High/Normal/Low)
- Per-user preferences
- Language preferences (English/Hindi/Marathi)
- Read receipts
- Action buttons (Approve/Reject from notification)

---

## 11. Mobile-First Features

### Critical Mobile Features

#### 1. **Offline Mode**
- Attendance can be marked offline
- Homework viewable offline
- Auto-sync when online
- Critical for Tier 2/3 cities

#### 2. **Push Notifications**
- Firebase Cloud Messaging
- Topic-based subscriptions
- Deep linking
- Quiet hours

#### 3. **Camera Integration**
- Photo upload (assignments, events)
- QR code scanning (attendance, ID)
- Document scanner

#### 4. **GPS Features**
- School bus tracking (parents)
- Geo-fenced attendance (teachers)
- School location

#### 5. **Biometric Login**
- Face ID / Fingerprint
- After first password login
- Quick app access

#### 6. **WhatsApp Integration**
- Share report cards
- Share fee receipts
- Quick communication
- Group messaging

#### 7. **Multi-Language**
- English (default)
- Hindi
- Marathi
- Tamil
- Telugu
- Kannada
- Gujarati

#### 8. **Voice Notes**
- For young students
- Quick parent communication
- Multilingual queries

#### 9. **Document Vault**
- Birth certificate
- TC, Bonafide
- Mark sheets
- Easy download/share

#### 10. **Smart Search**
- Global search
- Voice search
- Filter by class/section
- Auto-suggestions

---

## 12. Security & Compliance

### Data Security

- **Encryption at rest:** AES-256 for sensitive data
- **Encryption in transit:** TLS 1.3
- **JWT tokens:** Access (15 min) + Refresh (30 days)
- **Multi-tenant isolation:** Strict tenant_id enforcement
- **PII protection:** Student data encrypted
- **Backup:** Daily automated, 30-day retention

### Compliance

- **DPDP Act 2023** (India Data Protection)
- **Right to Education Act** compliance
- **Child safety regulations**
- **Audit logs** for sensitive actions
- **Parental consent** for minors
- **Data retention policies**

### Privacy Features

- Photo upload with consent
- Communication audit
- Visitor log
- Background verification for staff
- Anonymous reporting (bullying, harassment)

---

## 13. Deployment Strategy

### Infrastructure

```
┌─────────────────────────────────┐
│         Cloudflare (CDN)        │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│      AWS / DigitalOcean         │
│  ┌────────┐ ┌────────┐         │
│  │FastAPI │ │FastAPI │  ← LB   │
│  │Workers │ │Workers │         │
│  └────────┘ └────────┘         │
│       │         │               │
│  ┌────▼─────────▼────┐         │
│  │     MySQL         │         │
│  │  (Master + Read   │         │
│  │   Replicas)       │         │
│  └───────────────────┘         │
│                                 │
│  ┌─────────┐  ┌──────────┐    │
│  │ Redis   │  │   S3      │    │
│  │ Cluster │  │  Storage  │    │
│  └─────────┘  └──────────┘    │
└─────────────────────────────────┘
```

### Cost Estimation (100 schools)

- AWS/DigitalOcean: ₹25,000/month
- MySQL RDS: ₹15,000/month
- Redis: ₹5,000/month
- S3 Storage: ₹3,000/month
- SMS Gateway: ₹10,000/month (variable)
- Email: ₹2,000/month
- CDN: ₹3,000/month
- **Total: ~₹63,000/month for 100 schools**

### Revenue Estimation (100 schools, avg 500 students each)

- 500 students × ₹25/month × 100 schools = ₹12,50,000/month
- **Cost: ₹63,000 = 5%**
- **Net: ₹11,87,000/month** = ₹1.42 Cr/year (at 100 schools)

---

## 14. Phased Roadmap

### Total: 22 Phases | 10 Months | ~1,800 hours

| Phase | Module | Duration | Hours |
|-------|--------|----------|-------|
| 0 | Foundation (3 projects setup) | 4 days | 30 |
| 1 | Multi-Tenant Architecture | 7 days | 50 |
| 2 | Authentication & RBAC (13 roles) | 10 days | 70 |
| 3 | Super Admin (School Onboarding) | 10 days | 70 |
| 4 | School Admin Foundation | 7 days | 60 |
| 5 | Academic Setup (Class/Section/Subject) | 7 days | 50 |
| 6 | Student Information System | 10 days | 80 |
| 7 | Teacher Management | 7 days | 60 |
| 8 | Parent Module (Multi-Child) ⭐ | 10 days | 75 |
| 9 | Attendance Management | 7 days | 60 |
| 10 | Mobile App MVP Polish | 10 days | 80 |
| 11 | Fee Management | 14 days | 95 |
| 12 | Communication System | 7 days | 60 |
| 13 | Time Table & Substitution | 7 days | 60 |
| 14 | Homework & Assignment | 7 days | 60 |
| 15 | Examination System | 14 days | 90 |
| 16 | Report Cards | 7 days | 50 |
| 17 | Library Management | 5 days | 40 |
| 18 | Transport (with GPS) | 10 days | 70 |
| 19 | Hostel Management (Optional) | 7 days | 50 |
| 20 | Reports & Analytics | 7 days | 60 |
| 21 | Subscription & Billing | 7 days | 50 |
| 22 | Final Testing & Deployment | 10 days | 70 |

**Total: ~1,440 hours core + 360 hours buffer = ~1,800 hours**

---

## Key Success Metrics

### For Jaikalki (Business)
- Number of schools onboarded
- Monthly Recurring Revenue (MRR)
- Churn rate
- Customer Lifetime Value
- Net Promoter Score (NPS)

### For Schools
- Parent app adoption (>80%)
- Daily active users (>60%)
- Fee collection rate (>95%)
- Attendance accuracy (>99%)
- Communication delivery rate (>98%)

---

**Document Version:** 1.0
**Last Updated:** April 2026
**Next:** Phase-wise execution files
