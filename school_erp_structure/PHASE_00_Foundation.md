# Phase 0: Project Foundation - Jaikalki School ERP

**Project:** Jaikalki School ERP (Multi-Tenant SaaS)
**Project Path:** `C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp`
**Database:** `db_school_jaikalki`
**Duration:** 3-4 days
**Hours:** 30
**Priority:** CRITICAL (Must do first)

---

## Project Directory Structure

```
C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp\
├── erp_structure\               # Documentation
│   ├── SchoolERP_Architecture.md
│   ├── PHASE_00 to PHASE_22.md
│
├── school_backend\              # FastAPI Backend
│   ├── app\
│   ├── uploads\                 # ⭐ ALL FILES STORED HERE
│   │   ├── tenant_1\
│   │   ├── tenant_2\
│   │   └── ...
│   ├── alembic\
│   ├── tests\
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── .env
│
├── school_admin_web\            # React (Super Admin + School Admin)
│   ├── src\
│   ├── public\
│   ├── package.json
│   └── vite.config.ts
│
└── school_mobile\               # Flutter App (All other roles)
    ├── lib\
    ├── android\
    ├── ios\
    ├── web\
    └── pubspec.yaml
```

---

## Tech Stack

### Backend
- FastAPI 0.110+
- Python 3.11+
- SQLAlchemy 2.0 (async)
- Alembic (migrations)
- MySQL 8.0+
- Redis 7+
- Celery (background tasks)

### React Admin Web (Super Admin + School Admin)
- React 18 + Vite
- TypeScript
- Tailwind CSS + shadcn/ui
- TanStack Query
- React Router v6
- Zustand (state)
- Two-level access: Super Admin (Jaikalki) + School Admin (Per School)

### Flutter Mobile App (All Other Roles)
- Flutter 3.x
- flutter_bloc (state management)
- go_router (routing)
- get_it (DI)
- dio (HTTP)
- Single codebase: Android + iOS + Web
- Used by: School Admin (mobile), Principal, Teachers, Parents, Students, Staff

---

## Tasks

### Task 0.1: Backend Project Structure (4h)

```
school_backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── core/
│   │   ├── tenant.py            # ⭐ Multi-tenancy
│   │   ├── security.py
│   │   ├── permissions.py
│   │   └── middleware.py
│   ├── models/
│   ├── schemas/
│   ├── api/
│   │   ├── v1/                  # Regular APIs
│   │   └── admin/               # Super Admin APIs
│   ├── services/
│   ├── tasks/
│   └── utils/
├── alembic/
├── tests/
├── requirements.txt
├── docker-compose.yml
├── .env
└── README.md
```

### Task 0.2: requirements.txt (1h)

```txt
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
alembic==1.13.1
aiomysql==0.2.0
pymysql==1.1.0
cryptography==42.0.2
pydantic==2.6.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
redis==5.0.1
celery==5.3.6
python-dotenv==1.0.1
httpx==0.26.0
pytest==8.0.0
pytest-asyncio==0.23.5
razorpay==1.4.1                # Payment gateway
twilio==9.0.0                  # SMS
sendgrid==6.11.0               # Email
firebase-admin==6.4.0          # Push notifications
reportlab==4.1.0               # PDF generation
qrcode==7.4.2                  # QR codes
pillow==10.2.0                 # Image processing/optimization
aiofiles==23.2.1               # Async file operations
```

**Note:** No boto3/S3 - using local file storage instead.

### Task 0.3: Environment Configuration (2h)

`.env.example`:
```env
# App
APP_NAME=Jaikalki School ERP
DEBUG=true
ENVIRONMENT=development

# Company
COMPANY_NAME=Jaikalki Technology Pvt Ltd

# Database
DATABASE_URL=mysql+aiomysql://root:Love1718@localhost:3306/db_school_jaikalki?charset=utf8mb4
DATABASE_URL_SYNC=mysql+pymysql://root:Love1718@localhost:3306/db_school_jaikalki?charset=utf8mb4
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8080"]

# Local File Storage (No S3/MinIO)
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=10
MAX_IMAGE_WIDTH=1920
ALLOWED_FILE_TYPES=jpg,jpeg,png,pdf,docx,xlsx

# Storage limits per tenant (in MB)
STORAGE_LIMIT_BASIC=5120         # 5 GB
STORAGE_LIMIT_STANDARD=25600     # 25 GB
STORAGE_LIMIT_PREMIUM=102400     # 100 GB

# Payment Gateway (Razorpay)
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_secret

# SMS Gateway (Twilio or MSG91)
SMS_PROVIDER=msg91
MSG91_AUTH_KEY=your_key
MSG91_SENDER_ID=JKLKSC

# Email (SendGrid)
SENDGRID_API_KEY=your_key
SENDGRID_FROM_EMAIL=noreply@jaikalki.com

# Firebase (Push notifications)
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json

# Multi-tenant
DEFAULT_TENANT_LIMIT_STUDENTS=500
TRIAL_PERIOD_DAYS=30
```

### Task 0.4: Docker Compose (3h)

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: jaikalki_school_mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: Love1718
      MYSQL_DATABASE: db_school_jaikalki
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --max_connections=500

  redis:
    image: redis:7-alpine
    container_name: jaikalki_school_redis
    restart: always
    ports:
      - "6379:6379"

  phpmyadmin:
    image: phpmyadmin/phpmyadmin
    container_name: jaikalki_school_phpmyadmin
    restart: always
    environment:
      PMA_HOST: mysql
      MYSQL_ROOT_PASSWORD: Love1718
    ports:
      - "8080:80"
    depends_on:
      - mysql

volumes:
  mysql_data:
  redis_data:
```

**Note:** No MinIO/S3 service. Files stored directly in `school_backend/uploads/` directory.

### Task 0.5: FastAPI Main App (3h)

`app/main.py`:
- FastAPI instance
- CORS middleware
- Tenant detection middleware
- Health check endpoint
- Lifespan handler
- Exception handlers

### Task 0.6: Database Setup with Tenant Awareness (3h)

`app/database.py`:
- Async engine
- Session maker
- Base model with tenant_id
- Tenant query filter

### Task 0.7: Multi-Tenant Middleware (4h)

```python
# app/core/tenant.py
class TenantMiddleware:
    """Detects tenant from subdomain or JWT"""

    async def __call__(self, request, call_next):
        # Method 1: Subdomain detection
        host = request.headers.get('host', '')
        subdomain = host.split('.')[0]

        # Method 2: JWT-based (after auth)
        # Set tenant in request.state
        request.state.tenant_id = await get_tenant_id(subdomain)
        return await call_next(request)
```

### Task 0.7.1: Local File Storage Setup (4h) ⭐ NEW

```python
# app/core/file_storage.py
from pathlib import Path

class FileStorageConfig:
    BASE_PATH = Path("uploads")
    MAX_SIZE_MB = 10
    
    # Per-category allowed extensions
    ALLOWED_EXTENSIONS = {
        'photos': ['.jpg', '.jpeg', '.png'],
        'documents': ['.pdf', '.docx', '.jpg', '.png'],
        'reports': ['.pdf'],
        'attachments': ['.pdf', '.docx', '.xlsx', '.jpg', '.png'],
    }

# Create folder structure on startup
def setup_upload_directory():
    """Create uploads directory if doesn't exist"""
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Add .gitkeep
    gitkeep = upload_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
```

Add to `.gitignore`:
```
uploads/tenant_*/
!uploads/.gitkeep
```

Add to `main.py`:
```python
from fastapi.staticfiles import StaticFiles

# Mount uploads directory (with auth check via custom endpoint)
# DO NOT use StaticFiles directly - use protected endpoint
# This is just for development testing
```

### Task 0.8: React Admin Setup (4h)

```bash
npm create vite@latest school_admin_web -- --template react-ts
cd school_admin_web
npm install

# Tailwind + shadcn
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init

# Core dependencies
npm install react-router-dom@6 axios @tanstack/react-query
npm install zustand react-hook-form @hookform/resolvers zod
npm install lucide-react date-fns recharts
npm install @tanstack/react-table

# shadcn components
npx shadcn-ui@latest add button input label dialog table form
npx shadcn-ui@latest add dropdown-menu sheet tabs toast card
```

**Important:** This React app supports BOTH:
- **Super Admin** (Jaikalki) - `/super-admin/*`
- **School Admin** (Per School) - `/school-admin/*`

Routing logic detects role on login and routes accordingly.

### Task 0.9: Flutter App Setup (4h)

```bash
flutter create school_mobile
cd school_mobile

# Enable web
flutter config --enable-web

# Add dependencies (pubspec.yaml)
```

`pubspec.yaml`:
```yaml
name: jaikalki_school
description: Jaikalki School ERP

dependencies:
  flutter:
    sdk: flutter
  flutter_bloc: ^8.1.3
  equatable: ^2.0.5
  dio: ^5.4.0
  get_it: ^7.6.4
  go_router: ^13.0.0
  flutter_secure_storage: ^9.0.0
  local_auth: ^2.1.7
  geolocator: ^10.1.0
  image_picker: ^1.0.4
  firebase_messaging: ^14.7.6
  cached_network_image: ^3.3.0
  intl: ^0.18.1
  fl_chart: ^0.65.0
  pdf: ^3.10.7
  permission_handler: ^11.1.0
  connectivity_plus: ^5.0.2
  hive_flutter: ^1.1.0           # Offline storage
  flutter_localizations:
    sdk: flutter
  url_launcher: ^6.2.2
  share_plus: ^7.2.1
  qr_flutter: ^4.1.0             # QR generation
  mobile_scanner: ^3.5.6         # QR scanner
  webview_flutter: ^4.4.2        # For payment
  razorpay_flutter: ^1.3.6       # Payment
  flutter_local_notifications: ^16.3.2
```

### Task 0.10: Theme Setup (Jaikalki Branding) (3h)

Use Jaikalki colors:
- Primary Brown: `#3D2817`
- Gold: `#F4B71F`
- Light Gold: `#FFD66B`
- Warm White: `#FAFAF7`

### Task 0.11: Git & Documentation (2h)

- Initialize 3 repos (or monorepo)
- README files
- .gitignore
- Branch strategy

---

## Acceptance Criteria

### Backend
- [ ] FastAPI runs on `http://localhost:8000`
- [ ] `GET /health` returns 200
- [ ] `GET /docs` shows Swagger UI
- [ ] MySQL connected (db_school_jaikalki)
- [ ] Redis connected
- [ ] **`uploads/` directory created**
- [ ] **File upload endpoint working**
- [ ] **File serving with tenant isolation**
- [ ] Multi-tenant middleware in place

### React Admin Web (Super Admin + School Admin)
- [ ] Runs on `http://localhost:5173`
- [ ] Tailwind + shadcn working
- [ ] Login page renders
- [ ] **Routes for both Super Admin AND School Admin**
- [ ] Builds without errors

### Flutter Mobile
- [ ] Runs on Android emulator
- [ ] Runs on Chrome (web)
- [ ] Theme applied (Jaikalki colors)
- [ ] All dependencies installed

---

## Validation

```bash
# Backend
cd school_backend
docker-compose up -d              # Only MySQL + Redis + phpMyAdmin
pip install -r requirements.txt
uvicorn app.main:app --reload

curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "school-erp"}

# Verify uploads directory
ls school_backend/uploads/
# Should be empty initially

# Verify database
docker exec -it jaikalki_school_mysql mysql -u root -pLove1718 db_school_jaikalki -e "SELECT 1;"

# Test file upload (after auth)
curl -X POST http://localhost:8000/v1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.jpg" \
  -F "category=students" \
  -F "subcategory=photos"

# React Admin (Both Super Admin + School Admin)
cd school_admin_web
npm install
npm run dev
# Open http://localhost:5173
# Test: Login as super_admin → /super-admin/dashboard
# Test: Login as school_admin → /school-admin/dashboard

# Flutter
cd school_mobile
flutter pub get
flutter run -d chrome
```

---

## Claude Code Prompt

```
Read erp_structure/SchoolERP_Architecture.md sections 1-3 and 5-7.

Implement Phase 0 (Foundation) for Jaikalki School ERP as described.

PROJECT CONTEXT:
- Company: Jaikalki Technology Pvt Ltd
- Product: Multi-Tenant School ERP SaaS
- Project Path: C:\Users\Shyamveer\PycharmProjects\jaikalki_school_erp
- Database: db_school_jaikalki
- DB Password: Love1718

Create THREE projects:

1. school_backend/ (FastAPI)
   - Multi-tenant aware from start
   - MySQL with utf8mb4
   - Tenant detection middleware
   - All dependencies in requirements.txt
   - Docker compose: ONLY MySQL + Redis + phpMyAdmin (NO MinIO/S3)
   - **Local file storage in uploads/ directory**
   - **File upload service with tenant isolation**
   - **Image optimization with Pillow**
   - **Per-tenant folder structure (uploads/tenant_X/)**

2. school_admin_web/ (React + TypeScript) ⭐ TWO ADMIN LEVELS
   - For SUPER ADMIN (Jaikalki) AND SCHOOL ADMIN (Per School)
   - Vite + React 18 + TypeScript
   - Tailwind + shadcn/ui
   - **Two route groups:**
     * /super-admin/* (for Jaikalki super admin)
     * /school-admin/* (for school admin - full school control)
   - Role-based routing on login
   - Folder structure has separate features/super-admin/ and features/school-admin/
   - Branded as "Jaikalki School ERP - Admin Console"

3. school_mobile/ (Flutter)
   - For ALL ROLES INCLUDING School Admin (mobile version)
   - Single codebase, role-based UI
   - Android + iOS + Web
   - Branded as "Jaikalki School"
   - Apply Jaikalki theme (Brown #3D2817 + Gold #F4B71F)
   - School Admin gets simplified mobile UI for quick approvals

CRITICAL REQUIREMENTS:
- Multi-tenant architecture from day 1
- NO S3/MinIO - all files local in uploads/ directory
- Per-tenant folder isolation (uploads/tenant_1/, uploads/tenant_2/)
- File serving via authenticated endpoint (NOT static files)
- Image optimization on upload (Pillow)
- Storage quota enforcement per tenant
- Subdomain detection middleware
- All tables to have tenant_id (when added)
- Strong tenant isolation enforced
- Use SQLAlchemy 2.0 async style
- TypeScript strict mode in React
- Use go_router for Flutter routing

FOLDER STRUCTURE FOR FILES:
school_backend/uploads/
├── tenant_1/
│   ├── students/photos/
│   ├── students/documents/
│   ├── teachers/photos/
│   ├── teachers/documents/
│   ├── exams/question_papers/
│   ├── homework/assignments/
│   ├── fees/receipts/
│   ├── reports/report_cards/
│   ├── library/book_covers/
│   └── ...
└── tenant_2/
    └── (same structure)

REACT ROUTING STRUCTURE:
src/
├── features/
│   ├── super-admin/        # Jaikalki super admin features
│   └── school-admin/       # Per-school admin features (FULL CONTROL)
└── components/layouts/
    ├── SuperAdminLayout.tsx
    └── SchoolAdminLayout.tsx

Test all 3 projects run successfully before completing.
Verify uploads/ directory creation and file upload works.
```

---

## Next Phase

➡️ **Phase 1: Multi-Tenant Architecture** (PHASE_01_MultiTenant.md)
