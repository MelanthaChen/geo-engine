# GEO Publisher Agent Deployment Guide

This guide explains how to run the GEO Publisher Agent on a local Mac or Mac Mini. The backend runs on Render, the frontend runs on Vercel, and Reddit publishing happens locally because it requires an authenticated browser session through Playwright.

## Architecture Overview

```text
Researcher
   |
   v
GEO Frontend on Vercel
   |
   v
GEO Backend on Render
   |
   | 1. Content is marked pending for publishing
   v
Pending Publishing Queue
   ^
   | 2. Local Publisher Agent polls for pending tasks
   |
Mac / Mac Mini Publisher Agent
   |
   | 3. Playwright opens Reddit with local session state
   v
Reddit
   |
   | 4. Agent reports published URL back to Render backend
   v
GEO Backend on Render
```

## Prerequisites

- Python 3.12+
- Git
- Playwright
- Internet connection
- A Reddit account for publishing
- Access to the GEO Engine GitHub repository

## 1. Clone Repository

```bash
git clone <REPOSITORY_URL>
cd geo-engine
```

Replace `<REPOSITORY_URL>` with the GitHub repository URL.

## 2. Enter Backend Directory

```bash
cd backend
```

The publisher agent lives in the backend directory because it imports backend publishing utilities.

## 3. Create Virtual Environment

```bash
python3 --version
python3 -m venv venv
```

Confirm that the Python version is 3.12 or newer.

## 4. Activate Virtual Environment

```bash
source venv/bin/activate
```

After activation, the terminal prompt usually shows `(venv)`.

## 5. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Using `python -m pip` ensures packages install into the active virtual environment.

## 6. Install Playwright Browsers

```bash
python -m playwright install chromium
```

Use this command instead of `playwright install`. During deployment we found that `which playwright` and `which python` can point to different environments. Running Playwright as a Python module keeps the browser installation tied to the virtual environment being used by the publisher agent.

## 7. Generate `reddit_state.json`

```bash
python save_reddit_state.py
```

A Chromium browser window opens. Log in to Reddit manually in that browser. After Reddit login succeeds, return to the terminal and press Enter.

The script saves:

```text
backend/reddit_state.json
```

This file contains the local browser authentication state used by Playwright.

## 8. Start `publisher_agent.py`

```bash
python publisher_agent.py
```

The agent repeatedly polls the Render backend for pending publishing tasks.

The current backend URL is configured in `publisher_agent.py`:

```text
https://geo-engine.onrender.com
```

## 9. Verify Agent Operation

When the agent is running, expected terminal output includes one of these states:

```text
No pending tasks
```

or:

```text
Publishing content <id>
Published successfully
```

To test the full workflow:

1. Open the GEO frontend on Vercel.
2. Generate content.
3. Click Publish for a content item.
4. Confirm the local publisher agent detects the pending task.
5. Confirm Reddit receives the post.
6. Confirm the backend records the published URL.

## 10. Running on a Dedicated Mac Mini

For a dedicated Mac Mini:

1. Keep the Mac Mini connected to power and the internet.
2. Disable sleep in macOS System Settings.
3. Clone the repository on the Mac Mini.
4. Create the virtual environment on the Mac Mini.
5. Generate a fresh `reddit_state.json` on the Mac Mini.
6. Start the publisher agent from the Mac Mini terminal.

Recommended manual start command:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python publisher_agent.py
```

For long-running operation, use `tmux` or a macOS LaunchAgent after verifying the agent works manually.

Example `tmux` workflow:

```bash
tmux new -s geo-publisher
cd /path/to/geo-engine/backend
source venv/bin/activate
python publisher_agent.py
```

Detach from `tmux` without stopping the agent:

```text
Control-b, then d
```

Reattach later:

```bash
tmux attach -t geo-publisher
```

## Why `reddit_state.json` Is Local Only

`reddit_state.json` must stay local to each publisher machine.

- It is not stored in GitHub.
- It is not stored in Render.
- It is generated separately on every Mac or Mac Mini.
- It contains browser authentication state for Reddit.
- Committing it could expose a Reddit session to anyone with repository access.

Each user or machine must run:

```bash
python save_reddit_state.py
```

The generated file should remain only on that machine.

If `reddit_state.json` is already tracked in Git, remove it from Git tracking without deleting the local file:

```bash
git rm --cached backend/reddit_state.json
git commit -m "Stop tracking local Reddit authentication state"
```

## How Publishing Works

Publishing is split across cloud services and one local machine.

```text
Vercel Frontend
   |
   | User clicks Publish
   v
Render Backend
   |
   | Creates pending publishing task
   v
Local Publisher Agent
   |
   | Polls /api/v1/publishing/pending
   v
Playwright Chromium
   |
   | Uses local reddit_state.json
   v
Reddit
   |
   | Published URL returned
   v
Render Backend
```

The Render backend does not log in to Reddit and does not publish Reddit posts directly. It only stores content, exposes pending tasks, and records the final published URL. The local publisher agent performs the browser-based Reddit publishing step.
