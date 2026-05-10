# Jaikalki School ERP — Super Admin Console

React 19 + Vite + TypeScript + Tailwind + shadcn-style primitives. Used by
Jaikalki Technology staff to run the SaaS platform.

## Run

```bash
npm install
cp .env.example .env
npm run dev   # http://localhost:5173
```

The backend (`../school_erp_backend`) must be running on port 8000 for the
`/dashboard` health probe to succeed.

## Layout

```
src/
├── components/
│   ├── layouts/SuperAdminLayout.tsx
│   └── ui/        # shadcn-style primitives (button, card, input, label)
├── features/
│   ├── auth/      # Login (Phase 0 stub, real flow Phase 2)
│   ├── dashboard/ # Live API health + KPI placeholders
│   └── placeholder/
├── lib/           # api client, tailwind cn()
├── stores/        # zustand auth store
└── routes.tsx     # Route table
```

## Branding

Mirrors `../school_erp_designed/jaikalki-school-erp-design.html`:

| Token        | Hex      | Usage              |
| ------------ | -------- | ------------------ |
| `saffron`    | #E85D2E  | Primary action     |
| `marigold`   | #FFB800  | Highlights         |
| `teal`       | #0F766E  | Secondary action   |
| `indigo-dark`| #1F1248  | Text / backgrounds |
| `warm-white` | #FFFCF7  | Surface            |

Fonts: Fraunces (display), DM Sans (body), Noto Sans Devanagari (hindi),
JetBrains Mono — all loaded via Google Fonts.
