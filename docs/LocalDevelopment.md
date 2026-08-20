# Local Development

This guide runs GEO Engine entirely against a local PostgreSQL database. It does not change or depend on the Render database configuration.

## Local architecture

```text
Browser
  └─ Frontend: http://127.0.0.1:5173
       └─ Backend: http://127.0.0.1:8000
            └─ PostgreSQL 16: 127.0.0.1:5432/geo_engine

publisher_agent.py ─┐
retriever_agent.py ─┴─ Backend

Playwright ─ saved profiles in sessions/
```

Local defaults:

| Setting | Value |
|---|---|
| Database | `geo_engine` |
| Database user | `geo_user` |
| Database password | `geo_password` |
| PostgreSQL host | `127.0.0.1` |
| PostgreSQL port | `5432` |
| Backend | `http://127.0.0.1:8000` |
| Frontend | `http://127.0.0.1:5173` |

The local database password is only for development. Do not reuse it in production.

## Installation

### 1. Install PostgreSQL 16

On macOS with Homebrew:

```bash
brew install postgresql@16
brew services start postgresql@16
```

Confirm it is ready:

```bash
pg_isready -h 127.0.0.1 -p 5432
```

### 2. Create the local database and role

From the repository root:

```bash
./scripts/setup_local_db.sh
```

The script is idempotent. It starts Homebrew PostgreSQL when necessary and creates `geo_user` and `geo_engine` only when missing.

### 3. Install backend dependencies

Python 3.12 is the verified runtime:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements.txt
```

If `python3.12` is available on `PATH`, it can be used instead of the absolute path.

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Configure local environment variables

`backend/.env.local` is ignored by Git. Create it from the tracked example if it does not exist:

```bash
cp backend/.env.local.example backend/.env.local
```

It contains only local overrides:

```env
DATABASE_URL=postgresql://geo_user:geo_password@127.0.0.1:5432/geo_engine
BACKEND_URL=http://127.0.0.1:8000
PUBLISH_DRY_RUN=true
```

Keep API keys and any platform credentials in the existing ignored `backend/.env`. Environment variables loaded from `.env.local` take precedence when the startup scripts run.

### 6. Install Playwright browser support

The publishing and browser-backed provider workflows use the locally installed Google Chrome channel. If Playwright browser dependencies are missing, run:

```bash
backend/venv/bin/python -m playwright install chromium
```

Saved authentication profiles remain under `sessions/` and are independent of PostgreSQL.

## Startup

From the repository root:

```bash
./start_local.sh
```

The command:

1. Creates `backend/.env.local` from the example when missing.
2. Starts Homebrew PostgreSQL 16 if necessary.
3. Creates/verifies the local role and database.
4. Runs `alembic upgrade head` against the local database.
5. Starts the backend and frontend.
6. Waits for the backend health check.
7. Prints the local URLs and agent commands.

Logs and PID files are stored in the ignored `.local/` directory:

```text
.local/backend.log
.local/frontend.log
.local/backend.pid
.local/frontend.pid
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`

## Local agents

Run each agent in a separate terminal. Both commands explicitly load the local backend URL.

Publisher Agent:

```bash
cd backend
source venv/bin/activate
set -a
source .env.local
set +a
python -u publisher_agent.py
```

Retriever Agent:

```bash
cd backend
source venv/bin/activate
set -a
source .env.local
set +a
python -u retriever_agent.py
```

Expected startup messages include:

```text
[TRACE] publisher_agent backend_url=http://127.0.0.1:8000
[RETRIEVER] backend_url=http://127.0.0.1:8000
```

Agents remain local because browser profiles and Chrome are local resources. They poll the local FastAPI backend and never need Render in this workflow.

## Shutdown

Stop the backend and frontend while leaving PostgreSQL available:

```bash
./stop_local.sh
```

Stop all three services:

```bash
./stop_local.sh --postgres
```

PostgreSQL can also be managed directly:

```bash
brew services start postgresql@16
brew services restart postgresql@16
brew services stop postgresql@16
```

Stop agents with `Ctrl+C` in their terminals.

## Running migrations

Load the local overrides before running Alembic manually:

```bash
set -a
source backend/.env.local
set +a
cd backend
venv/bin/python -m alembic upgrade head
```

Check the current revision and repository head:

```bash
venv/bin/python -m alembic current
venv/bin/python -m alembic heads
```

Both should report the same revision. The verified revision when this guide was written is `20260806_0015`.

Create a new migration only when a schema change is intentional:

```bash
venv/bin/python -m alembic revision --autogenerate -m "description"
```

Review generated migrations before applying them.

## Seed data

The backend seeds the minimum default Property on startup:

```text
Name: GeoAIResume
Domain: geoairesume-web-six.vercel.app
```

Demo platform accounts are seeded lazily when the accounts endpoint or a workflow requiring them is first used:

```bash
curl 'http://127.0.0.1:8000/api/v1/accounts?property_id=1'
```

No production data is copied into the local database.

## Database reset

The reset command destroys only the local `geo_engine` database, recreates it, and runs all migrations:

```bash
./stop_local.sh
./reset_local_db.sh
./start_local.sh
```

The reset script requires typing `RESET`. For non-interactive local automation:

```bash
./reset_local_db.sh --yes
```

Never point `backend/.env.local` at Render before using the reset script. The reset script uses the explicit local host, port, database, and user defaults rather than parsing a production URL.

## Direct database access

```bash
PGPASSWORD=geo_password psql \
  -h 127.0.0.1 \
  -p 5432 \
  -U geo_user \
  -d geo_engine
```

Useful checks:

```sql
SELECT version_num FROM alembic_version;
SELECT id, name, domain FROM properties;
SELECT id, platform, handle, session_status FROM accounts;
```

## Browser sessions

Local PostgreSQL stores account/session metadata. Browser cookies and profile data remain in ignored local directories:

```text
sessions/reddit/profile
sessions/xiaohongshu/creator/profile
sessions/xiaohongshu/web/profile
sessions/perplexity/profile
```

Refresh a profile when the platform requests login:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py reddit
python save_platform_state.py xiaohongshu --purpose creator
python save_platform_state.py xiaohongshu --purpose web
python save_platform_state.py perplexity
```

Publishing remains review-only: automation fills the platform form and waits for manual confirmation. A local environment does not automatically submit content.

## Verification commands

Backend health:

```bash
curl http://127.0.0.1:8000/health
```

Frontend:

```bash
curl -I http://127.0.0.1:5173
```

Database:

```bash
PGPASSWORD=geo_password psql \
  -h 127.0.0.1 -p 5432 -U geo_user -d geo_engine \
  -c 'SELECT version_num FROM alembic_version;'
```

Provider status:

```bash
curl http://127.0.0.1:8000/api/v1/providers/status
```

Citation Test and Experiment Lab should be exercised from their frontend pages. Those checks may call configured external LLM providers even though all application state is local.

## Troubleshooting

### PostgreSQL is not accepting connections

```bash
brew services restart postgresql@16
pg_isready -h 127.0.0.1 -p 5432
```

Inspect Homebrew services:

```bash
brew services list
```

### Role or database does not exist

```bash
./scripts/setup_local_db.sh
```

### Backend still connects to Render

Confirm the agent/backend command loaded `.env.local`:

```bash
set -a
source backend/.env.local
set +a
```

Then verify without printing credentials:

```bash
backend/venv/bin/python -c \
  'from app.core.config import settings; print(settings.DATABASE_URL.rsplit("@", 1)[-1])'
```

Expected:

```text
127.0.0.1:5432/geo_engine
```

### Backend fails during startup

```bash
tail -n 100 .local/backend.log
```

Common causes are a stopped database, missing virtual environment, missing API key in `backend/.env`, or unapplied migrations.

### Frontend does not load

```bash
tail -n 100 .local/frontend.log
cd frontend && npm install
```

### Port already in use

Check ports:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

Stop the prior local workflow with `./stop_local.sh` or terminate the conflicting development process.

### Agent points to Render

The agent startup line must report:

```text
backend_url=http://127.0.0.1:8000
```

If it does not, stop the agent, load `backend/.env.local`, and restart it.

### Browser profile is missing or expired

Run the relevant `save_platform_state.py` command from the Browser sessions section. Database resets do not delete browser profiles.

### Alembic revision mismatch

```bash
set -a
source backend/.env.local
set +a
cd backend
venv/bin/python -m alembic current
venv/bin/python -m alembic heads
venv/bin/python -m alembic upgrade head
```

### Docker Compose is already using PostgreSQL port 5433

The existing `docker-compose.yml` database is a separate optional local instance on port `5433`. The Homebrew workflow in this guide uses port `5432`. Do not run both against the same `DATABASE_URL` accidentally.

## Production isolation

This workflow does not modify:

- Render environment variables
- Render PostgreSQL
- Vercel configuration
- `DEPLOYMENT.md` production commands
- production service definitions

Only ignored local environment/runtime files and the local PostgreSQL instance are used.
