# GEO Engine Troubleshooting

The canonical troubleshooting guide now lives at:

- [docs/Troubleshooting.md](docs/Troubleshooting.md)

Start there for current guidance on:

- missing Reddit profile;
- Reddit security challenges;
- Xiaohongshu retrieval login;
- Xiaohongshu Creator login;
- wrong browser profile;
- queues stuck in queued or processing;
- publisher agent polling;
- retriever agent polling;
- database migrations;
- Render deployment;
- Playwright launch issues.

For platform initialization, read:

- [docs/PlatformSetup.md](docs/PlatformSetup.md)

Quick checks:

```bash
cd backend
source venv/bin/activate
python -m playwright install chromium
alembic upgrade head
curl http://localhost:8000/health
```

Local agents:

```bash
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
BACKEND_URL=http://localhost:8000 python -u retriever_agent.py
```

Render agents:

```bash
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
BACKEND_URL=https://geo-engine.onrender.com python -u retriever_agent.py
```
