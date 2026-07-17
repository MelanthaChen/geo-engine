# Troubleshooting

This guide collects common GEO Engine problems. Each issue includes symptoms, root cause, and resolution.

## Missing Reddit Profile

Symptoms:

```text
No saved browser profile found for reddit
No saved storage state found for reddit
```

Root Cause:

The local Reddit profile was never created, was deleted, or the database still points to an old storage-state path.

Resolution:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py reddit
```

Verify:

```bash
ls -la ../sessions/reddit/profile
```

## Reddit Session Expired

Symptoms:

- Reddit asks for login again.
- Review page opens but user is logged out.
- Reddit shows a security or JS challenge.

Root Cause:

Reddit invalidated cookies or challenged the Playwright browser profile.

Resolution:

```bash
cd backend
source venv/bin/activate
rm -rf ../sessions/reddit/profile
python save_platform_state.py reddit
```

If Reddit blocks Playwright before login, confirm that normal Chrome works on the same network and retry later.

## Reddit Browser Shows `Unsupported command-line flag: --no-sandbox`

Symptoms:

Chrome banner says:

```text
You are using an unsupported command-line flag: --no-sandbox
```

Root Cause:

Playwright may inject default browser flags. This is not necessarily from GEO code.

Resolution:

Use standalone diagnostics to compare Playwright behavior. Do not assume publisher logic is broken until a minimal Playwright script succeeds.

## Xiaohongshu Retrieval Account Not Logged In

Symptoms:

- `retriever_agent.py` fails.
- Xiaohongshu retrieval returns login page or empty posts.
- Frontend remains in retrieving state or returns retrieval failure.

Root Cause:

The web retrieval profile is missing or expired.

Resolution:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py xiaohongshu --purpose web
```

Verify:

```bash
ls -la ../sessions/xiaohongshu/web/profile
```

## Xiaohongshu Creator Account Not Logged In

Symptoms:

- Publisher redirects to Creator login.
- `/api/galaxy/user/info` returns 401.
- Publish page never mounts.

Root Cause:

The Creator profile is missing, expired, or was saved before publish authorization completed.

Resolution:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py xiaohongshu --purpose creator
```

Wait until the script verifies Creator publish authorization before pressing Enter.

## Wrong Xiaohongshu Browser Profile

Symptoms:

- Retrieval works but publishing fails.
- Publishing works but retrieval fails.
- Login appears valid in one workflow but not another.

Root Cause:

Retrieval and publishing require separate browser profiles.

Resolution:

Use the correct profile:

```text
retrieval: sessions/xiaohongshu/web/profile/
publishing: sessions/xiaohongshu/creator/profile/
```

Reinitialize the profile that is failing.

## Queue Stuck in `queued`

Symptoms:

- Publishing Queue shows jobs as queued.
- Nothing happens in browser.

Root Cause:

No local agent is running, or the agent is pointing to the wrong backend.

Resolution:

```bash
cd backend
source venv/bin/activate
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

For local backend:

```bash
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
```

## Job Stuck in `processing`

Symptoms:

- Job was claimed but never completed.
- Agent was interrupted or crashed.

Root Cause:

The local agent exited after claiming the task, or an exception occurred before status update.

Resolution:

Check agent logs. If this is development data, create a new job through the frontend/API. Avoid manually editing production state unless you understand the queue model.

## Publisher Agent Not Polling Render

Symptoms:

Agent logs show local URL or wrong backend.

Root Cause:

`BACKEND_URL` is unset or wrong.

Resolution:

```bash
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

Check startup log:

```text
[TRACE] publisher_agent backend_url=https://geo-engine.onrender.com
```

## Retriever Agent Not Polling Render

Symptoms:

Xiaohongshu retrieval task is created, but local browser never opens.

Root Cause:

`retriever_agent.py` is not running or is pointed at the wrong backend.

Resolution:

```bash
BACKEND_URL=https://geo-engine.onrender.com python -u retriever_agent.py
```

Expected idle log:

```text
[RETRIEVER] no pending Xiaohongshu retrieval tasks
```

## CORS Errors

Symptoms:

Frontend console shows CORS blocked requests.

Root Cause:

Frontend origin is not allowed by backend CORS configuration.

Resolution:

Check `backend/main.py` CORS origins. Local dev should use:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Vercel preview domains are allowed by regex.

## Database Migration Problems

Symptoms:

- `UndefinedColumn`
- missing table errors
- backend fails during request handling
- Alembic head mismatch

Root Cause:

Database schema does not match SQLAlchemy models or migrations were not applied.

Resolution:

```bash
cd backend
source venv/bin/activate
alembic current
alembic heads
alembic upgrade head
```

For development only, destructive reset:

```bash
python reset_database.py
alembic upgrade head
```

## Render Deployment Fails on Settings Validation

Symptoms:

Render logs show Pydantic settings validation errors.

Root Cause:

Required environment variable missing.

Resolution:

Set required Render env vars:

```text
OPENAI_API_KEY
DATABASE_URL
BACKEND_URL
```

Reddit credentials should not be required for backend boot because publishing is local.

## Playwright Browser Executable Missing

Symptoms:

```text
BrowserType.launch: Executable doesn't exist
```

Root Cause:

Playwright Python package exists but browsers were not installed for that environment.

Resolution:

```bash
cd backend
source venv/bin/activate
python -m playwright install chromium
```

## `which python` and `which playwright` Mismatch

Symptoms:

Commands use different environments.

Root Cause:

Global Playwright executable is being used instead of the backend virtual environment.

Resolution:

Always run Playwright through Python:

```bash
python -m playwright install chromium
```

Start agents with:

```bash
venv/bin/python -u publisher_agent.py
```

## Frontend Shows No AI FAQs But Content Generates

Symptoms:

AI FAQ content appears, but the FAQ panel says no FAQs.

Root Cause:

Frontend state mapping or response rendering issue.

Resolution:

Inspect the response from:

```text
GET /api/v1/content/faqs/{target}?mode=ai&content_type=...&property_id=...
```

Confirm the frontend assigns returned FAQ rows to the AI FAQ panel state.

## Xiaohongshu Trending Posts Not Appearing

Symptoms:

Frontend displays retrieving forever or no posts.

Root Cause:

Retriever agent is not running, web profile is logged out, or retrieval task failed.

Resolution:

1. Start `retriever_agent.py`.
2. Confirm `sessions/xiaohongshu/web/profile/` exists.
3. Reinitialize web profile if needed.
4. Check backend retrieval task logs/status.

## Publish Page Opens But Editor Does Not Appear

Symptoms:

Xiaohongshu Creator page opens but title/body fields are missing.

Root Cause:

Creator workflow requires switching to `上传图文` and uploading an image before the editor mounts.

Resolution:

Current publisher should switch tabs and upload the development placeholder image. If it fails, inspect the Creator page DOM because Xiaohongshu may have changed its UI.

## History Delete or Preview Fails

Symptoms:

History card delete fails or preview does not clear.

Root Cause:

Related record may already be deleted, or delete endpoint may not handle that event type.

Resolution:

Check backend delete route and `history/delete_history_service.py`. Confirm the event type maps to FAQ, content, audit, publishing job, or citation test.

## Local Browser Profile Corruption

Symptoms:

Profile opens but login state behaves inconsistently.

Root Cause:

Browser profile files may be corrupted or partially written.

Resolution:

Delete and recreate only the affected profile:

```bash
rm -rf sessions/reddit/profile
rm -rf sessions/xiaohongshu/web/profile
rm -rf sessions/xiaohongshu/creator/profile
```

Then rerun the matching `save_platform_state.py` command.
