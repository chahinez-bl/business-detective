# Deployment guide (for the product owner / developer — customers never do any of this)

Goal: customers visit **https://yourdomain.com**, sign up, and use the product. Nothing to install.

## Option A — one container (recommended, simplest)

The `Dockerfile` builds the React app and serves **site + API from one origin** (no CORS needed).

1. Create a PostgreSQL database (managed service recommended: Neon, Supabase, Railway, Render, AWS RDS…). Copy its URL as
   `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`.
2. Create a persistent volume mounted at `/data/storage` (uploads and PDF reports live here — back it up).
3. Deploy the repo root as a Docker web service (Render, Railway, Fly.io, Google Cloud Run + volume, a VPS…). Set:
   ```
   APP_ENV=production
   SECRET_KEY=<python -c "import secrets;print(secrets.token_urlsafe(48))">
   DATABASE_URL=postgresql+psycopg://...
   STORAGE_DIR=/data/storage
   ```
   The container runs `alembic upgrade head` on start, then the server (`$PORT` honoured).
4. Point your domain at the service and enable HTTPS (all hosts above do this automatically).
5. Optional build arg for the contact page: `--build-arg VITE_CONTACT_EMAIL=you@domain.com`.

**Self-host on one machine:** `cp .env.example .env`, set `SECRET_KEY` and `POSTGRES_PASSWORD`, run `docker compose up -d --build`, put Caddy/nginx with HTTPS in front of port 8000.

## Option B — frontend and backend hosted separately

**Backend** (any Python host): `pip install -r backend/requirements.txt`, set the env vars above plus
`CORS_ORIGINS=https://app.yourdomain.com`, run
`cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`.
Install the `fonts-dejavu-core` system package for best PDF text coverage.

**Frontend** (Vercel / Netlify / Cloudflare Pages / S3+CDN): root `frontend`, build `npm run build`, output `dist`.
Build env: `VITE_API_URL=https://api.yourdomain.com` (and optionally `VITE_CONTACT_EMAIL`).
Add an SPA fallback rewrite of every path to `/index.html` (Netlify `_redirects`: `/* /index.html 200`; Vercel: rewrite `/(.*)` → `/index.html`).

## Environments

| | development | staging | production |
|---|---|---|---|
| `APP_ENV` | development | staging | production |
| Tables | auto-created | `alembic upgrade head` | `alembic upgrade head` |
| `SECRET_KEY` | optional (insecure fallback) | required | required, 32+ chars |
| API docs `/api/docs` | on | on | **off** |
| Database | SQLite file | PostgreSQL (separate DB) | PostgreSQL |

Never reuse staging secrets or databases in production; never commit `.env`.

## Operations checklist

* HTTPS only; set HSTS at the proxy. Back up PostgreSQL and the `/data/storage` volume together.
* Upgrades: deploy new image → migrations run automatically. Create new migrations with
  `cd backend && alembic revision --autogenerate -m "describe change"` and review them.
* Scale-out: the in-memory login throttle is per process — add gateway rate limiting; files must live on shared storage.
* Monitoring: `/api/health` for uptime checks. Logs contain error types and references, never customer data.
* Optional AI: set `AI_PROVIDER=openai_compatible`, `AI_API_URL`, `AI_API_KEY`, `AI_MODEL`. Only summarised facts are sent; replies containing numbers not present in the facts are discarded. To use a private/local model, point `AI_API_URL` at your own OpenAI-compatible server.
