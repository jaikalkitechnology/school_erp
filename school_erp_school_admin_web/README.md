# Jaikalki School ERP — School Admin Console

React 19 + Vite + TypeScript + Tailwind. Each school's admin signs in here at
their own subdomain (e.g. `dpsschool.jaikalki.com`).

## Run

```bash
npm install
cp .env.example .env
npm run dev   # http://localhost:5174
```

The backend (`../school_erp_backend`) must be running on port 8000 for the
dashboard health probe.

## Layout

```
src/
├── components/
│   ├── layouts/SchoolAdminLayout.tsx   # Sidebar with all school modules
│   └── ui/        # shadcn-style primitives
├── features/
│   ├── auth/      # Login (Phase 0 stub)
│   ├── dashboard/ # KPIs + API health
│   └── placeholder/  # Generic page used by routes that ship later
├── lib/           # api client (axios), tailwind cn()
├── stores/        # zustand auth store (persists JWT)
└── routes.tsx
```

## Branding

Same design tokens as the super-admin console — see
`../school_erp_designed/jaikalki-school-erp-design.html`.
