# Business Detective

**Turn your business data into decisions.** Business Detective is a web-based SaaS for business monitoring and decision support. A business owner signs up in the browser, uploads a CSV or Excel export, and gets: what is happening, what changed, what needs attention, why, how much it may cost, and what to do — then turns recommendations into tracked actions and PDF reports.

> The customer needs **only a web browser**. Python, Node.js, a terminal and `localhost` are for developers deploying the product — never for end customers.

```
DATA → UNDERSTAND → MONITOR → DETECT → EXPLAIN → DECIDE → ACT
```

## Customer journey (all verified in a real browser — see *Testing*)

Public website → Get started → Register → Create business workspace → Upload CSV/XLSX → Data-quality check → Confirm column mapping → Analyze → Overview → Monitoring → Insights → Recommendations → Decision Center → Actions → PDF report. Customers can sign out and return later; everything persists per business.

## Architecture

```
Browser ─► React + TypeScript + Vite SPA  (public website + private app, code-split)
              │  HTTPS, Bearer token
              ▼
          FastAPI (Python)  ── routers → services → analytics engine (pandas/numpy/scipy)
              │                         └→ reportlab (server-side PDF)
              ├─► SQLAlchemy ─► SQLite (dev) / PostgreSQL (production)   [Alembic migrations]
              └─► private file storage (uploads + PDFs; never publicly served)
```

```
backend/app/
  config.py database.py models.py schemas.py security.py deps.py errors.py main.py
  analytics/  mapping · quality · capabilities · engine · simulator · assistant · demo   (pure functions, no web code)
  services/   ingest (safe uploads) · workspace (persistence + read-models) · reports (PDF)
  routers/    auth · businesses · datasets · workspace · actions · reports · demo
frontend/src/  api/ state/ layouts/ components/ pages/public/ pages/app/
```

**Data model:** `User` → `BusinessMember(role)` → `Business` → `Dataset` → `Analysis` → `Insight` → `Recommendation` → `Action`; `Report`; `RevokedToken` (logout). A new upload never deletes earlier datasets. Every business-scoped query is checked against the caller's membership; non-members get `404`, so ids cannot be probed. Roles: `owner`, `admin`, `member`, `viewer` (read-only).

## What it does

| Area | Behaviour |
|---|---|
| Import | CSV (`, ; tab |`, UTF‑8/cp1252) and XLSX. Drag & drop, progress, preview. EN/FR header detection (`CA`, `Qty`, `Article`, `TransactionDate`, `SalesAmount`…), manual override. |
| Data quality | Score 0‑100; rows received / accepted / rejected, duplicates, invalid dates and numbers, negatives, missing values, short history — each with consequence and fix. Nothing is dropped silently. |
| Capability-driven analytics | Only analyses the data supports are produced; others show *“This analysis is unavailable because your dataset does not contain the required information…”* |
| Analyses | Sales trends · unusual days (weekday‑aware robust z‑score) · 7‑day shifts · period‑over‑period **contribution** by product/category · product declines/rises · stockout risk & repeated stockouts · supplier cost drift & concentration · margins, below‑cost sales, margin trend · customers (active/new/lost, concentration) · returns · **forecast** (≥28 days, back‑tested on your own recent data, labelled by reliability). |
| Monitoring | Per‑area status (Normal / Attention / Warning / Critical), prioritized alerts (severity from impact vs. monthly revenue, confidence, urgency), recent events, opportunities. |
| Insights | Each has WHAT / WHY / IMPACT / EVIDENCE / ACTION; technical detail under “Details”. “Possible contributing factors”, never false certainty. Impact is only shown when it can be estimated: *“Financial impact cannot be reliably estimated from the available data.”* |
| Decision Center | “What should I do today?” — Critical / High / Medium with problem, impact, evidence, action, confidence. |
| Actions | Create from any insight/recommendation, assign, due date, note, To do → In progress → Resolved, archive. |
| What‑if | Price / cost / volume simulator on your real averages, explicitly labelled *SIMULATION*; optional user‑supplied elasticity. |
| Assistant | Rule‑based, grounded in stored results; says *“I don't have enough data to answer that reliably.”* Optional external AI may only rephrase facts and is **rejected if it introduces any number not in the facts**. |
| Reports | Server‑side PDF: summary, KPIs, health, alerts with evidence, opportunities, trends, forecast, recommendations, actions. |
| Currency | Per business (DZD, EUR, USD, GBP, MAD, TND, CAD, CHF, AED, SAR). Re‑run the analysis after changing it. |
| Demo | `Explore demo` shows fictional **Nova Market** (computed in memory, labelled “Demo data — fictional”). It is never stored in, or mixed with, a customer workspace. |

## Local development (developers only)

```bash
# backend  (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env            # defaults work for development (APP_ENV=development creates tables automatically)
uvicorn app.main:app --reload --port 8000        # API docs: http://127.0.0.1:8000/api/docs

# frontend  (Node 18+), second terminal
cd frontend
npm install
npm run dev                            # http://localhost:5173  (proxies /api to 127.0.0.1:8000)
```

Single‑process (like production): `cd frontend && npm run build`, then run uvicorn — it serves `frontend/dist` automatically at `http://127.0.0.1:8000`.

Sample files to try: `data/samples/*` (different structures, one French/semicolon/cp1252, one XLSX with customers and costs; regenerate with `python backend/scripts/make_samples.py`).

## Testing

```bash
cd backend && python -m pytest -q                 # 69 tests: engine, quality, mapping, API, auth, upload, actions, reports, isolation, roles
cd frontend && npm run build                      # TypeScript type-check + production build
# real-browser acceptance test of the whole customer journey (needs a running server with the built frontend):
pip install playwright && playwright install chromium
python e2e/journey.py http://127.0.0.1:8000
```

## Configuration

All settings are environment variables — see [`.env.example`](.env.example). In `staging`/`production` the app refuses to start without a strong `SECRET_KEY`, docs endpoints are disabled and tables come from migrations (`alembic upgrade head`) rather than `create_all`.

## Deployment

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** (single container / Docker Compose, or frontend + backend + managed PostgreSQL hosted separately).

## Security & privacy

Bcrypt password hashing · JWT sessions with server‑side logout revocation · login throttling · role‑based authorization and business‑level isolation on every endpoint · upload allow‑list (`.csv`/`.xlsx`), size and row limits, magic‑byte checks, zip‑bomb guard, random on‑disk names, sanitized display names · uploads/reports only served through authenticated endpoints · friendly errors, no stack traces · logs contain error types only, never dataset values · security headers · CORS restricted to configured origins · external AI off by default. Details in [docs/SECURITY.md](docs/SECURITY.md) and the in‑app [privacy notice](frontend/src/pages/public/Pages.tsx).

## Known limitations (honest list)

* **Verified here:** backend tests (SQLite), frontend build, and a full real‑browser journey on Chromium. **Not verified here:** PostgreSQL runtime, Docker build, a live external AI provider, Safari/Firefox.
* Login throttling is per process (in memory); behind several instances add a gateway/Redis rate limit.
* Session token is kept in `localStorage` (simple, but exposed to XSS); a hardened deployment may prefer HttpOnly cookies + CSRF protection.
* No email flows (verification, password reset, invitations): teammates must already have an account. No billing: the pricing page is a placeholder.
* Analyses run synchronously inside the request (fine for the 15 MB / 300k‑row default limits; use a job queue for larger files).
* Stock is read as “units on hand when the row was recorded”; cost as **per‑unit** purchase cost; ambiguous `1,234` is read as one thousand two hundred thirty‑four; ambiguous `05/06/2026` is read day/month (and the user is told). Mapping help text states these assumptions.
* Impact numbers are estimates from history, not guarantees; causes are *possible contributing factors*.
* Changing the currency does not rewrite old analyses; use “Re‑run analysis” in Settings.
* PDF uses DejaVu fonts when installed (Docker image does); otherwise Helvetica (non‑Latin text may show as `?`).
* The contact page opens the visitor's email app (`VITE_CONTACT_EMAIL`); there is no server‑side mail sending.
* Operator duties before charging customers: publish legal terms/privacy policy, back up the database and file volume, run behind HTTPS.
