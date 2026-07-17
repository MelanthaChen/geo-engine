# Platform Setup

This guide explains how to initialize every external platform used by GEO Engine from a clean machine.

Run all commands from the repository root unless instructed otherwise. Browser profiles are local authentication state. They are intentionally not stored in GitHub, Render, or Vercel.

## Prerequisites

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Google Chrome must be installed on the machine because the project launches Playwright with `channel="chrome"` where platform login requires a normal desktop browser.

## Profile Storage Layout

```text
geo-engine/
  sessions/
    reddit/
      profile/
    xiaohongshu/
      web/
        profile/
      creator/
        profile/
```

Do not commit `sessions/`. These folders contain cookies, browser storage, localStorage, IndexedDB, service workers, and other authentication state.

## Reddit

### Purpose

Reddit is used as a publishing platform. GEO prepares Reddit-native discussion posts and opens Reddit in Review Mode so a human can inspect and decide whether to submit.

### Required Account

Use one Reddit account that is allowed to create posts in the target subreddit. For development, the backend currently sends the target as `test` unless configured otherwise.

### Browser Requirements

- Local Google Chrome installation.
- Playwright Python package.
- A local persistent Chrome profile under `sessions/reddit/profile/`.

### Important Session Note

Reddit login state is not permanent. You may need to regenerate or refresh the profile after:

- logging out manually;
- browser profile corruption;
- expired cookies;
- Reddit security challenges;
- moving to another machine;
- deleting `sessions/reddit/profile/`;
- changing network/IP in a way that triggers Reddit security checks.

### Initialize Reddit From Scratch

```bash
cd backend
source venv/bin/activate
python save_platform_state.py reddit
```

A Chrome window opens at Reddit login. Log in manually. If Reddit shows a security challenge, complete it if possible.

When login succeeds, return to the terminal and press Enter.

### Stored Location

```text
sessions/reddit/profile/
```

The current architecture uses a persistent Chrome profile for Reddit. It should not rely on `reddit_state.json` or `storage_state.json` for new setup.

### Verify Reddit Profile

Check that the folder exists:

```bash
ls -la ../sessions/reddit/profile
```

Run the publisher agent only after a publishing job exists:

```bash
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
```

For Render:

```bash
BACKEND_URL=https://geo-engine.onrender.com python -u publisher_agent.py
```

Expected signs of success:

- agent claims a Reddit publishing job;
- Chrome opens using the Reddit profile;
- Reddit submission page opens;
- title/body are prepared for review.

### Common Reddit Failure Cases

#### Reddit Shows Security Challenge Before Login

Cause: Reddit may challenge Playwright-launched browsers even with `channel="chrome"`.

Resolution:

- try again later;
- complete any visible challenge;
- regenerate the profile;
- confirm normal Chrome can access Reddit from the same network;
- use the standalone diagnostic scripts only for debugging, not normal setup.

#### Profile Folder Missing

Symptom:

```text
No saved browser profile found for reddit
```

Resolution:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py reddit
```

#### Reddit Asks for Login Again

Cause: cookies expired or profile was invalidated.

Resolution:

```bash
rm -rf ../sessions/reddit/profile
python save_platform_state.py reddit
```

Only remove the profile if you are prepared to log in again.

#### Old Account Row Points to `storage_state.json`

Older database rows may contain:

```text
/sessions/reddit/storage_state.json
```

The local resolver should map legacy session references to the canonical Reddit profile. If it does not, inspect `accounts.session_path` and regenerate seeded accounts.

## Xiaohongshu / Rednote

Xiaohongshu requires two independent browser profiles because retrieval and publishing use different web applications and different authentication contexts.

### Required Separation

Use two independent accounts if possible:

1. Retrieval account: used by `retriever_agent.py` to search and read Xiaohongshu/Rednote posts.
2. Publishing account: used by `publisher_agent.py` to open Creator Center and prepare posts.

These roles must remain separate in research workflows to avoid mixing browsing/retrieval activity with publishing activity.

## Xiaohongshu Retrieval Account

### Purpose

The retrieval account searches Xiaohongshu/Rednote for topic-related posts. It retrieves titles, authors, likes, publish time, hashtags, body text, comments, URLs, and metadata when available.

### Browser Profile

```text
sessions/xiaohongshu/web/profile/
```

### Agent

```bash
python -u retriever_agent.py
```

### Initialize Retrieval Profile

```bash
cd backend
source venv/bin/activate
python save_platform_state.py xiaohongshu --purpose web
```

The browser opens:

```text
https://www.rednote.com/
```

Log in with the retrieval account. After login succeeds and the home/search experience is accessible, return to the terminal and press Enter.

### Verify Retrieval Login

```bash
ls -la ../sessions/xiaohongshu/web/profile
```

Start the retriever agent:

```bash
BACKEND_URL=http://localhost:8000 python -u retriever_agent.py
```

Expected output includes:

```text
[RETRIEVER] Xiaohongshu retriever_agent started
[RETRIEVER] no pending Xiaohongshu retrieval tasks
```

When a task exists, expected output includes claimed task ID and retrieved count.

## Xiaohongshu Publishing Account

### Purpose

The publishing account opens Xiaohongshu Creator Center and prepares a note for human review. The agent switches to the image/text publishing tab, uploads a placeholder image when needed, fills title/body, and stops before final publishing.

### Browser Profile

```text
sessions/xiaohongshu/creator/profile/
```

### Agent

```bash
python -u publisher_agent.py
```

### Initialize Publishing Profile

```bash
cd backend
source venv/bin/activate
python save_platform_state.py xiaohongshu --purpose creator
```

The browser opens:

```text
https://creator.xiaohongshu.com/
```

After QR/login, the script verifies that the real Creator publish page is accessible. It should not be considered complete until the publish page or upload UI is reachable.

The verification checks pages such as:

```text
https://creator.rednote.com/publish/publish
https://creator.xiaohongshu.com/publish/publish
```

Only after publish authorization is verified should you press Enter to save the profile.

### Verify Publishing Login

```bash
ls -la ../sessions/xiaohongshu/creator/profile
```

Run publisher agent with a queued Xiaohongshu job:

```bash
BACKEND_URL=http://localhost:8000 python -u publisher_agent.py
```

Expected successful Review Mode output includes:

```text
Launching creator profile...
Creator profile loaded.
Publish page detected.
Switching to 上传图文...
image uploaded=true
Xiaohongshu editor mounted
READY_FOR_REVIEW
```

## Why Two Xiaohongshu Profiles Are Required

Retrieval uses the consumer website:

```text
https://www.rednote.com/
```

Publishing uses Creator Center:

```text
https://creator.xiaohongshu.com/
https://creator.rednote.com/
```

These sites use different authentication flows, cookies, localStorage, and redirect behavior. A profile that can browse Rednote search may not be authorized to access Creator publishing, and a Creator profile should not be reused for retrieval experiments.

## Refreshing Xiaohongshu Login

If retrieval or publishing starts redirecting to login:

```bash
# Retrieval profile
rm -rf ../sessions/xiaohongshu/web/profile
python save_platform_state.py xiaohongshu --purpose web

# Publishing profile
rm -rf ../sessions/xiaohongshu/creator/profile
python save_platform_state.py xiaohongshu --purpose creator
```

Only delete a profile when you are ready to log in again.

## Common Xiaohongshu Mistakes

### Using One Account for Both Roles

This breaks the research separation between observation and publishing. Use separate accounts and profiles.

### Deleting Profile Folders

Deleting `sessions/xiaohongshu/web/profile/` or `sessions/xiaohongshu/creator/profile/` removes login state. Reinitialize with `save_platform_state.py`.

### Mixing Browser Profiles

Do not point retrieval at the creator profile or publishing at the web profile. The agents expect their own profile paths.

### Running the Wrong Agent

- Xiaohongshu retrieval requires `retriever_agent.py`.
- Xiaohongshu publishing requires `publisher_agent.py`.

### Creator Profile Saved Too Early

If the Creator profile was saved before the publish page was accessible, publishing may redirect to login. Re-run:

```bash
python save_platform_state.py xiaohongshu --purpose creator
```

Wait until publish authorization is verified before pressing Enter.

## Platform Setup Checklist

On a new machine, complete all required setup:

```text
[ ] backend virtual environment created
[ ] Python dependencies installed
[ ] Playwright Chromium installed
[ ] backend/.env configured
[ ] database migrated
[ ] Reddit profile initialized if Reddit publishing is needed
[ ] Xiaohongshu web profile initialized if Xiaohongshu retrieval is needed
[ ] Xiaohongshu creator profile initialized if Xiaohongshu publishing is needed
[ ] retriever_agent.py tested
[ ] publisher_agent.py tested
```
