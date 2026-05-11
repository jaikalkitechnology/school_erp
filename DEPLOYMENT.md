# Jaikalki School ERP — Deployment

This is the runbook for taking the platform to production. The backend ships
as a Docker image; the two React apps build to static bundles served by your
edge CDN / nginx.

## 1. Prerequisites

- Linux host with Docker 24+ and Docker Compose v2.
- A managed MySQL 8.0 cluster (or self-hosted; the compose file bundles one
  for single-node deployments).
- A managed Redis instance.
- **Node.js 20.19+** (or 22.12+) on whatever box builds the React apps —
  Vite 8 refuses to run on Node 18, which is past end-of-life anyway.
  Install via NodeSource (`curl -fsSL https://deb.nodesource.com/setup_20.x
  | sudo -E bash - && sudo apt-get install -y nodejs`) or nvm.
- **Python 3.11** for the backend (Dockerfile pins it; only matters if
  you build outside Docker).
- Two DNS names you control: one for the super-admin web (e.g.
  `admin.example.com`) and a wildcard for the school admin
  (`*.school.example.com`). The wildcard is what `TenantMiddleware` reads.
- TLS termination at your reverse proxy. The backend listens on plain HTTP;
  nginx / Caddy / a managed LB does TLS.

## 2. Backend image

```bash
cd school_erp_backend
cp .env.example .env  # fill in real secrets
docker compose -f docker-compose.prod.yml --profile migrate run --rm migrator
docker compose -f docker-compose.prod.yml up -d backend
```

The migrator profile runs `alembic upgrade head` once and exits, then the
backend service starts behind its own healthcheck (`/v1/health`).

To seed the platform tenant + a demo school + the default super admin
account on first boot:

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.services.seed
```

Default users (change passwords immediately):

| Subdomain  | Email                  | Password    | Role         |
|------------|------------------------|-------------|--------------|
| `platform` | `admin@jaikalki.com`   | `Admin@123` | super_admin  |
| `demo`     | `admin@demo.school`    | `School@123`| school_admin |

## 3. Frontends

Each React app is a Vite build. Run from the repo root:

```bash
cd school_erp_super_admin_web
npm ci && VITE_API_BASE_URL=https://api.example.com npm run build
# dist/ is your static bundle. Upload to S3/CloudFront, or:
rsync -av dist/ root@host:/var/www/super_admin/

cd ../school_erp_school_admin_web
npm ci && VITE_API_BASE_URL=https://api.example.com npm run build
rsync -av dist/ root@host:/var/www/school_admin/
```

Sample nginx vhost:

```nginx
server {
    listen 443 ssl http2;
    server_name admin.example.com;
    root /var/www/super_admin;
    location / { try_files $uri /index.html; }
    location /v1/ { proxy_pass http://backend:8000; proxy_set_header Host $host; }
    location /admin/ { proxy_pass http://backend:8000; proxy_set_header Host $host; }
}
server {
    listen 443 ssl http2;
    server_name ~^(?<sub>[^.]+)\.school\.example\.com$;
    root /var/www/school_admin;
    location / { try_files $uri /index.html; }
    location /v1/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant-Subdomain $sub;
    }
}
```

The `X-Tenant-Subdomain` header is the contract the backend reads for tenant
resolution; the React apps send it automatically on every axios call when
the host doesn't already encode the subdomain.

## 4. Mobile

The Flutter app under `school_erp_mobile/jaikalki/` builds with the standard
toolchain:

```bash
cd school_erp_mobile/jaikalki
flutter pub get
flutter build apk --release      # or:
flutter build appbundle --release
```

Set the `API_BASE_URL` env var (passed via `--dart-define`) to your
production API host.

## 5. CI / CD

`.github/workflows/ci.yml` runs four jobs on every push + PR:
- backend pytest (the full 164-case suite + `alembic upgrade head` against
  SQLite),
- super-admin web `tsc --noEmit` + `npm run build`,
- school-admin web `tsc --noEmit` + `npm run build`,
- Flutter `flutter analyze` + `flutter test`.

For continuous deploy, add a fifth job that pushes the backend image to your
registry on `main` and triggers a rolling restart on the host.

## 6. Backups

- **MySQL**: `mysqldump --single-transaction --routines --triggers` nightly
  to S3 with 30-day retention. Phase 1 isolates each school under a
  `tenant_id` column; restore can be filtered per tenant.
- **Uploads volume**: `restic` snapshot of `/app/uploads/` on the same
  cadence. The directory is partitioned per `tenant_X/` so per-school
  restores are isolated.

## 7. Monitoring

- The backend writes JSON access logs to stdout (uvicorn defaults). Pipe
  to your log aggregator.
- Wire `/v1/health` into your uptime check.
- The Phase 12 `notification_outbox` is your dead-letter queue for SMS /
  email failures — alert on `status='failed'` accumulation.
