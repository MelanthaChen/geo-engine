# GEO Engine Deployment Guide

This guide summarizes how to run GEO Engine across cloud services and local agents. For complete platform login/profile setup, read [docs/PlatformSetup.md](docs/PlatformSetup.md).

## Deployment Model

```mermaid
flowchart TD
    V[Vercel Frontend] --> R[Render Backend]
    R --> DB[(PostgreSQL)]
    PA[Local publisher_agent.py] --> R
    RA[Local retriever_agent.py] --> R
    PA --> Chrome1[Local Chrome Profiles]
    RA --> Chrome2[Local Chrome Profiles]
    Chrome1 --> Platforms[Reddit / Xiaohongshu Creator]
    Chrome2 --> XHS[Xiaohongshu Web]
```

Render and Vercel do not own platform login state. Browser profiles are created and used locally.

## Prerequisites

- Python 3.12+
- Node.js and npm
- PostgreSQL
- Git
- Google Chrome
- Playwright Python package
- OpenAI API key
- Reddit account if Reddit publishing is required
- Xiaohongshu retrieval account if Xiaohongshu retrieval is required
- Xiaohongshu Creator/publishing account if Xiaohongshu publishing is required

## Clone Repository

```bash
git clone <REPOSITORY_URL>
cd geo-engine
```

## Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Use `python -m playwright install chromium`, not a global `playwright install`, so Playwright browsers are installed for the same Python environment used by the agents.

Create `backend/.env`:

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
BACKEND_URL=http://localhost:8000
PUBLISH_DRY_RUN=true
```

For agents connected to Render, use:

```env
BACKEND_URL=https://geo-engine.onrender.com
```

## Database Setup

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

Development reset only:

```bash
python reset_database.py
alembic upgrade head
```

## Run Backend Locally

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Platform Initialization

Run these from `backend/` with `venv` active.

```bash
# Reddit publishing profile
python save_platform_state.py reddit

# Xiaohongshu retrieval profile
python save_platform_state.py xiaohongshu --purpose web

# Xiaohongshu Creator publishing profile
python save_platform_state.py xiaohongshu --purpose creator
```

Profile locations:

```text
sessions/reddit/profile/
sessions/xiaohongshu/web/profile/
sessions/xiaohongshu/creator/profile/
```

These folders are local authentication state and must not be committed.

## Run Local Agents

Publisher agent:

```bash
cd backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

Retriever agent for Xiaohongshu:

```bash
cd backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u retriever_agent.py
```

Use `http://localhost:8000` instead of the Render URL for local backend testing.

## Dedicated Mac Mini Operation

For a dedicated publishing/retrieval machine:

1. Disable sleep in macOS settings.
2. Clone the repository.
3. Install backend dependencies.
4. Initialize all required browser profiles on that Mac.
5. Run agents in `tmux` or another process supervisor.

Example:

```bash
tmux new -s geo-agents
cd /path/to/geo-engine/backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

Use a second `tmux` session for `retriever_agent.py` if Xiaohongshu retrieval is required.

## Render Backend

Set environment variables in Render:

```text
OPENAI_API_KEY
DATABASE_URL
BACKEND_URL
```

Optional:

```text
GOOGLE_SEARCH_API_KEY
GOOGLE_SEARCH_ENGINE_ID
GITHUB_TOKEN
XIAOHONGSHU_RETRIEVAL_LIMIT
```

Do not upload Reddit or Xiaohongshu browser profiles to Render.

## Vercel Frontend

Deploy `frontend/` to Vercel. Ensure the frontend points to the Render backend or local backend according to the current frontend API configuration.

## Verification Checklist

```text
[ ] Backend /health returns healthy
[ ] Frontend loads dashboard
[ ] Database migrations are applied
[ ] Default Property exists
[ ] Reddit profile initialized if needed
[ ] Xiaohongshu web profile initialized if needed
[ ] Xiaohongshu creator profile initialized if needed
[ ] retriever_agent.py polls backend
[ ] publisher_agent.py polls backend
[ ] Website Audit can run
[ ] AI FAQ can generate
[ ] Platform retrieval works for selected platform
[ ] Publishing job reaches Review Mode
```

## More Documentation

- [README.md](README.md)
- [docs/PlatformSetup.md](docs/PlatformSetup.md)
- [docs/Workflow.md](docs/Workflow.md)
- [docs/Architecture.md](docs/Architecture.md)
- [docs/Troubleshooting.md](docs/Troubleshooting.md)
