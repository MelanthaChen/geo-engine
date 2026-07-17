# GEO Engine

GEO Engine is a research platform for running Generative Engine Optimization experiments across website analysis, platform retrieval, content generation, publishing review workflows, and citation testing.

The project is designed for research use. A professor, research assistant, or developer should be able to select a tracked property, discover what people and AI systems ask about a category, generate grounded content, prepare platform-native posts, and measure whether language models mention or cite the target property.

## Project Overview

GEO Engine is property-centric. A Property represents the website or brand being studied, such as:

```text
Property: GeoAIResume
Domain: geoairesume-web-six.vercel.app
Brand: GeoAIResume
```

Once a Property is selected, the entire application operates in that context:

- Website Audit analyzes the Property website.
- Social Media Track discovers AI FAQs, Reddit questions, or Xiaohongshu posts.
- Content generation uses the selected Property and retrieved evidence.
- Publishing Queue creates review tasks for local publishing agents.
- Citation Tests evaluate whether models mention the Property.
- Content History records generated artifacts and workflow events.

## Motivation

Traditional SEO systems optimize for search engine ranking pages. GEO Engine is built around a different research question: how can content, evidence, platform discussions, and publishing workflows influence what generative engines retrieve, summarize, mention, or cite?

The platform supports experiments around:

- AI FAQ discovery.
- Real platform retrieval.
- Website GEO audits.
- Platform-native content preparation.
- Human review publishing.
- Citation and mention testing.
- Historical experiment tracking.

## Architecture

```mermaid
flowchart TD
    F[Vercel Frontend] --> B[Render or Local FastAPI Backend]
    B --> DB[(PostgreSQL)]
    B --> Q1[Publishing Jobs]
    B --> Q2[Retrieval Tasks]
    PA[Local publisher_agent.py] --> B
    RA[Local retriever_agent.py] --> B
    PA --> PW1[Playwright Browser]
    RA --> PW2[Playwright Browser]
    PW1 --> Reddit[Reddit / Xiaohongshu Creator]
    PW2 --> XHS[Xiaohongshu / Rednote Web]
    B --> OAI[OpenAI API]
```

Cloud services manage application state. Local agents handle browser work that cannot reliably run on Render, especially publishing and Xiaohongshu retrieval.

## Features

- Property selector similar to Google Search Console.
- Website Audit with crawl results, GEO score components, and recommendations.
- AI FAQ generation from LLM reasoning.
- Reddit Platform FAQ generation from retrieved Reddit questions.
- Xiaohongshu Trending Posts retrieval through a local browser retriever.
- Platform-aware content generation.
- Publishing Queue with platform-specific formatters.
- Human Review Mode for publishing instead of automatic posting.
- Citation Tests for prompt-based visibility experiments.
- Experiment Lab for Princeton GEO paper reproduction work.
- History timeline for FAQ, content, audit, publish, and citation events.

## Folder Structure

```text
geo-engine/
  backend/
    app/
      api/v1/                 FastAPI routes
      core/                   settings, database, dependencies
      models/                 SQLAlchemy models
      services/               business logic
        faq_discovery/        AI FAQ and platform FAQ services
        platform_retrievers/  Reddit and Xiaohongshu retrievers
        platform_formatters/  Reddit and Xiaohongshu formatters
        platform_publishers/  Publisher registry and adapters
        website_audit/        crawler, analyzer, scoring, recommendations
      experiment/             Experiment Lab orchestration
      ge/                     Princeton GEO-style retrieval/generation modules
      evaluation/             Experiment evaluation logic
      storage/                Experiment persistence repository
    alembic/                  database migrations
    publisher_agent.py        local publishing worker
    retriever_agent.py        local Xiaohongshu retrieval worker
    save_platform_state.py    browser profile initialization
    reset_database.py         development database reset script
  frontend/
    src/
      components/             reusable UI components
      contexts/               Property context
      layouts/                dashboard layout
      pages/                  routed dashboard pages
  docs/                       project documentation
  sessions/                   local browser profiles; never commit secrets
  external/                   external research/retrieval dependencies
```

## Technology Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic Settings.
- Frontend: React, TypeScript, Vite, Tailwind, shadcn/ui-style components, Recharts.
- LLM: OpenAI API.
- Browser automation: Playwright with locally installed Google Chrome.
- Deployment: Render backend, Vercel frontend, local Mac or Mac Mini workers.
- Database: PostgreSQL locally or managed PostgreSQL on Render.

## Installation

Clone the repository:

```bash
git clone <REPOSITORY_URL>
cd geo-engine
```

Create the backend environment:

```bash
cd backend
python3 --version
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Install frontend dependencies:

```bash
cd ../frontend
npm install
```

## Environment Variables

Create `backend/.env`:

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
BACKEND_URL=http://localhost:8000

# Optional
GITHUB_TOKEN=
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
REDDIT_USERNAME=
REDDIT_PASSWORD=
PUBLISH_DRY_RUN=true
ACCOUNT_ID=
AGENT_NAME=
XIAOHONGSHU_RETRIEVAL_COMMAND=
XIAOHONGSHU_RETRIEVAL_TIMEOUT_SECONDS=180
XIAOHONGSHU_RETRIEVAL_LIMIT=20
```

Notes:

- `OPENAI_API_KEY` and `DATABASE_URL` are required by the backend settings.
- Reddit username/password are optional. Publishing uses local browser profiles, not password login.
- `BACKEND_URL` is required for local agents. Use `https://geo-engine.onrender.com` when agents should talk to the deployed backend.
- `ACCOUNT_ID` can restrict `publisher_agent.py` to one account. Leave blank for the generic pending endpoint.

Frontend environment variables depend on the current API client implementation. If the frontend expects a backend URL, set it to either local or Render according to the frontend API configuration.

## Database Setup

From `backend/` with the virtual environment active:

```bash
alembic upgrade head
```

For development only, the project also includes a destructive reset script:

```bash
python reset_database.py
alembic upgrade head
```

The backend also imports all SQLAlchemy models and runs `Base.metadata.create_all(bind=engine)` at startup. Alembic is still the preferred way to initialize schema consistently.

Verify the backend can connect:

```bash
python - <<'PY'
from app.core.database import engine
with engine.connect() as conn:
    print('database ok')
PY
```

## Running Backend

From `backend/`:

```bash
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"healthy"}
```

## Running Frontend

From `frontend/`:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

Build check:

```bash
npm run build
npm run lint
```

## Running Background Agents

Agents must run on a local machine with Chrome and Playwright access.

### Publisher Agent

The publisher agent polls publishing jobs and prepares posts in the platform browser. It does not blindly auto-post; the current workflow leaves content ready for human review.

Local backend:

```bash
cd backend
source venv/bin/activate
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
```

Render backend:

```bash
cd backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

### Xiaohongshu Retriever Agent

Xiaohongshu retrieval runs locally because it requires a persistent logged-in browser profile.

```bash
cd backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u retriever_agent.py
```

Use `http://localhost:8000` instead of the Render URL for local backend testing.

## Platform Initialization

Platform initialization is required before a new machine can retrieve or publish. Browser profiles are local machine state and are not stored in GitHub, Render, or Vercel.

Read the full guide before running agents:

- [docs/PlatformSetup.md](docs/PlatformSetup.md)

Quick commands:

```bash
cd backend
source venv/bin/activate

# Reddit publishing profile
python save_platform_state.py reddit

# Xiaohongshu retrieval profile
python save_platform_state.py xiaohongshu --purpose web

# Xiaohongshu publishing profile
python save_platform_state.py xiaohongshu --purpose creator
```

Local profile locations:

```text
sessions/reddit/profile/
sessions/xiaohongshu/web/profile/
sessions/xiaohongshu/creator/profile/
```

## Common Workflow

```mermaid
flowchart TD
    A[Select Property] --> B[Run Website Audit]
    B --> C[Generate AI FAQ or Platform Signals]
    C --> D[Generate Content]
    D --> E[Queue Publish]
    E --> F[Local Publisher Agent]
    F --> G[Human Review in Browser]
    G --> H[Record Review / Publish Status]
    H --> I[Run Citation Test]
    I --> J[History Timeline]
```

Typical researcher workflow:

1. Create or select a Property.
2. Run Website Audit to understand the target site.
3. Generate AI FAQs for predictive questions.
4. Generate Reddit Platform FAQs or Xiaohongshu Trending Posts.
5. Generate content grounded in the selected signal source.
6. Queue content for the selected platform.
7. Run the local publisher agent.
8. Review the prepared browser page manually.
9. Run citation tests.
10. Inspect History.

## Troubleshooting

See:

- [docs/Troubleshooting.md](docs/Troubleshooting.md)
- [docs/PlatformSetup.md](docs/PlatformSetup.md)

Common quick checks:

```bash
# backend env
cd backend
source venv/bin/activate
python -m playwright install chromium

# database
alembic current
alembic upgrade head

# backend
curl http://localhost:8000/health

# agents
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
BACKEND_URL=http://localhost:8000 python -u retriever_agent.py
```

## Developer Guide

### Add a New Platform

1. Add a retriever under `backend/app/services/platform_retrievers/` if the platform supports retrieval.
2. Register it in `platform_retrievers/registry.py`.
3. Add a formatter under `platform_formatters/`.
4. Register it in `platform_formatters/registry.py`.
5. Add a publisher under `platform_publishers/` if browser publishing is supported.
6. Register it in `platform_publishers/registry.py`.
7. Add any browser session path to `SessionResolver` only if the platform needs local browser state.
8. Document platform setup in `docs/PlatformSetup.md`.

### Add a New Agent

1. Create a top-level script in `backend/`.
2. Load `BACKEND_URL` from settings.
3. Poll a backend endpoint for queued work.
4. Execute one task at a time.
5. Report completion or failure to the backend.
6. Add logs that identify task ID, platform, and status.
7. Document startup commands.

### Add a New API

1. Create a route module in `backend/app/api/v1/`.
2. Keep routes thin.
3. Put business logic in `backend/app/services/`.
4. Register the router in `backend/main.py`.
5. Add schemas if request/response models are reused.
6. Document endpoints if they affect setup or workflow.

### Add a New Queue

1. Create a SQLAlchemy model with explicit statuses.
2. Add service functions for create, claim, complete, and fail.
3. Add thin API routes for polling and status transitions.
4. Ensure every state transition creates a History event when relevant.
5. Add an agent only if work must run locally.

### Add Database Models

1. Add the SQLAlchemy model in `backend/app/models/`.
2. Import it from `backend/app/models/__init__.py` if needed by metadata creation.
3. Create an Alembic migration.
4. Run `alembic upgrade head` on every environment.
5. Update reset/development docs if the table is required for boot.

## FAQ

### Does Render publish to Reddit or Xiaohongshu?

No. Render stores content and queues. Local agents use Playwright and local browser profiles for platform work.

### Are browser profiles committed to GitHub?

No. `sessions/` contains machine-specific authentication state and must stay local.

### Why are there two Xiaohongshu profiles?

Retrieval and publishing use different sites and authentication contexts. Retrieval uses `www.rednote.com`; publishing uses the Creator Center.

### Why does Reddit sometimes require reinitialization?

Reddit may expire cookies, invalidate sessions, show security challenges, or block Playwright browser fingerprints. Regenerate the local profile when that happens.

### What should I run first on a new machine?

1. Install backend dependencies.
2. Install Playwright browsers.
3. Configure `.env`.
4. Initialize the database.
5. Initialize Reddit and Xiaohongshu browser profiles.
6. Start backend, frontend, retriever agent, and publisher agent.
