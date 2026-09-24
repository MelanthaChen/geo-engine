# Production Readiness

## Purpose

The same repository now supports two explicit runtime modes:

- **Local development** loads `backend/.env`, permits loopback services, and uses the local GeoAIResume demo page by default.
- **Production** reads configuration only from process environment variables, rejects loopback database/demo/backend URLs, and requires explicit frontend CORS origins.

No Render hostname, production database URL, public demo URL, or secret is stored in source. This work did not deploy or connect to Render, Vercel, or any production database.

## Backend environment contract

### Local development

Create `backend/.env` from `backend/.env.local.example` and configure:

```text
APP_ENV=development
DATABASE_URL=postgresql://...@127.0.0.1:5433/geo_engine
OPENAI_API_KEY=...
DEMO_TARGET_URL=http://127.0.0.1:8000
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
BACKEND_URL=http://127.0.0.1:8000
PUBLISH_DRY_RUN=true
```

The committed Docker PostgreSQL service publishes container port 5432 as host port 5433. Direct backend launches, Alembic, `start_local.sh`, and `scripts/setup_local_db.sh` all use the single `DATABASE_URL` from `backend/.env`. The older ignored `backend/.env.local` file is no longer part of normal startup.

Start the local database when necessary:

```bash
docker compose up -d postgres
```

Start the application:

```bash
./start_local.sh
```

### Render production

Configure these variables manually on the Render backend service:

| Variable | Required | Production rule |
|---|---:|---|
| `APP_ENV` | Yes | Set exactly to `production`. |
| `DATABASE_URL` | Yes | Use the active Render PostgreSQL connection value. Do not guess it or copy the local URL. Loopback hosts are rejected. |
| `OPENAI_API_KEY` | Yes | Supply a valid key through Render secrets/environment configuration. Never use `backend/.env`. |
| `DEMO_TARGET_URL` | Yes | Public HTTPS URL of the deployed GeoAIResume target page. Loopback and non-HTTPS values are rejected. |
| `FRONTEND_ORIGINS` | Yes | Comma-separated allowed browser origins, normally the production Vercel URL and any intentional custom domain. |
| `BACKEND_URL` | Yes | Public HTTPS URL of the deployed Render backend. The production validator rejects localhost. |
| `PUBLISH_DRY_RUN` | Recommended | Keep `true` unless publishing is intentionally enabled. |
| `GOOGLE_SEARCH_API_KEY` | Optional | Needed only for non-demo live Google Custom Search retrieval. The frozen professor demo does not need it. |
| `GOOGLE_SEARCH_ENGINE_ID` | Optional | Paired with `GOOGLE_SEARCH_API_KEY`. |
| `GITHUB_TOKEN` | Optional | Only for workflows that use GitHub access. |
| `REDDIT_USERNAME`, `REDDIT_PASSWORD` | Optional | Not required for backend startup or the professor demo. |

In production, `backend/app/core/config.py` does not load any dotenv file. Missing or unsafe production values cause startup to fail with a specific validation message.

## Vercel frontend configuration

Configure manually in the Vercel frontend project:

```text
VITE_API_BASE_URL=https://<the-render-backend-host>
```

Development may omit this value and use `http://127.0.0.1:8000`. A production bundle no longer silently uses that fallback: when `VITE_API_BASE_URL` is absent, the application throws a clear configuration error before making an API request.

All API calls and generated download/artifact links use the shared `frontend/src/api/config.ts` value.

## Demo target and frozen references

`DEMO_TARGET_URL` controls both:

1. the seeded GeoAIResume property's target URL; and
2. recognition of that property as the frozen professor-demo workflow.

Development defaults to `http://127.0.0.1:8000` only when `APP_ENV` is not production. Production requires an explicitly supplied public HTTPS value.

The audited target snapshot is still fetched from the configured target URL during validation. It is inserted at source rank 1 and target index 0. The target content-integrity hash remains enforced.

The four verified reference snapshots are now stored in the tracked immutable asset:

```text
backend/app/experiment/data/geoairesume_reference_pack.json
```

That asset contains the frozen evaluation query, Princeton GEO-Bench source-row provenance, the four real reference URLs, and the exact reference texts. Runtime validation recalculates each text hash and compares it with the committed manifest in `demo_reference_pack.py`. Ordering is fixed at ranks 2–5:

1. HBR
2. Novorésumé
3. Grammarly
4. UMass Global

The application no longer needs the ignored local `backend/experiment_dataset/` cache to load this professor-demo pack. No local database rows are required to initialize it on a clean production database.

## Database configuration and migrations

The application engine and Alembic both import the same validated `settings.DATABASE_URL`. `alembic.ini` contains no database URL.

Run migrations from the backend directory:

```bash
APP_ENV=production alembic upgrade head
```

The remaining production variables must be present in the process environment when this command runs. The expected revision is:

```text
20260923_0020
```

The clean-database migration path was repaired for the legacy first migration, which materializes current SQLAlchemy metadata. Revisions 0017–0020 now detect schema objects already created by that legacy behavior while continuing to perform normal incremental upgrades on older databases.

Local verification created a disposable PostgreSQL database, migrated it from zero to `20260923_0020`, confirmed the three Teacher Pipeline tables and four new experiment-document provenance columns, and removed the database afterward.

## Startup and Playwright

Expected Render Docker start command:

```text
alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
```

This is the existing `backend/Dockerfile` command. It requires only valid environment variables and reachable PostgreSQL/OpenAI/public demo services. It does not require a local database, local resume server, worker, or browser session to start.

Playwright remains available for explicitly invoked publishing, retrieval, account-session, and citation workflows. Importing and starting FastAPI does not call `sync_playwright()`, launch a browser, or validate browser dependencies. A backend startup smoke test reached `/health` with no Playwright initialization in the startup log.

The Playwright-based container image and package remain unchanged because browser functionality has not been removed.

## Verification performed

- Backend test suite: 27 passed.
- Backend module compilation: passed.
- Fresh backend startup and `/health`: passed.
- Playwright initialization during startup: none observed.
- Clean disposable PostgreSQL migration: reached `20260923_0020` and schema checks passed.
- Frozen reference pack: four texts, URLs, ranks, and SHA-256 hashes passed.
- Production configuration dry run with dummy non-secret external values: passed.
- Production loopback database rejection: passed.
- Production loopback demo-target rejection: passed.
- Missing production frontend origins rejection: passed.
- Frontend lint: passed.
- Frontend production build with an explicit dummy HTTPS API URL: passed.
- Repository search for `dpg-da1ngbbutv3s73ffaeug-a`: no tracked occurrence.

The existing local professor dataset remains in the local Docker database. The configuration change does not copy, delete, or alter those records. The frozen-pack integrity and local backend smoke tests pass with the development defaults. A new paid OpenAI end-to-end experiment was not generated as part of production-readiness configuration testing.

## Deployment checklist for the operator

1. Create or select the intended Render PostgreSQL resource.
2. Set the Render variables listed above, using that resource's actual `DATABASE_URL`.
3. Deploy a public HTTPS GeoAIResume page whose audited target content matches the verified demo target, then set `DEMO_TARGET_URL` to it.
4. Set `FRONTEND_ORIGINS` to the Vercel origin.
5. Deploy the backend and confirm the migration log reaches `20260923_0020` before Uvicorn starts.
6. Set Vercel `VITE_API_BASE_URL` to the deployed backend URL and rebuild the frontend.
7. Verify `/health`, CORS, OpenAI authentication, Audit, Teacher Validation, dataset creation, and both exports in production.

No production system was changed or contacted during this readiness work.
