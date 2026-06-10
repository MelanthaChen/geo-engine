# Common Deployment Issues

This guide lists common deployment problems for the GEO Publisher Agent and how to fix them. Run all commands from the repository unless a step says otherwise.

## Issue: `source venv/bin/activate` Fails

### Cause

The virtual environment does not exist, the command is being run from the wrong directory, or there is a typo in the path.

### Fix

Go to the backend directory and create the virtual environment again:

```bash
cd /path/to/geo-engine/backend
python3 -m venv venv
source venv/bin/activate
```

After activation, verify Python is coming from `venv`:

```bash
which python
python --version
```

Expected path shape:

```text
/path/to/geo-engine/backend/venv/bin/python
```

## Issue: `BrowserType.launch: Executable doesn't exist`

### Cause

Playwright is installed as a Python package, but the Chromium browser binary has not been installed for that Python environment.

### Fix

Activate the virtual environment and install Chromium through Python:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python -m playwright install chromium
```

Do not use only `playwright install`; it may run a different Playwright executable from a different environment.

## Issue: `which playwright` and `which python` Point to Different Locations

### Cause

This indicates a virtual environment mismatch. Python may be running from the project `venv`, while the `playwright` command may be coming from a global installation or another Python environment.

Example mismatch:

```text
which python
/path/to/geo-engine/backend/venv/bin/python

which playwright
/opt/homebrew/bin/playwright
```

### Fix

Use Playwright through the active Python environment:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python -m playwright install chromium
```

Then start the agent with the same Python:

```bash
python publisher_agent.py
```

## Issue: `reddit_state.json` Missing

### Cause

The Reddit browser session has not been generated on this machine. The state file is intentionally local and is not committed to GitHub.

### Fix

Generate the state file:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python save_reddit_state.py
```

Log in to Reddit in the browser window. Return to the terminal and press Enter when login is complete.

Confirm the file exists:

```bash
ls -l reddit_state.json
```

## Issue: Reddit Asks for Login Again

### Cause

The saved Reddit session expired, was invalidated, or no longer matches the browser context used by Playwright.

### Fix

Regenerate the state file:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python save_reddit_state.py
```

Log in again, then restart the publisher agent:

```bash
python publisher_agent.py
```

## Issue: `publisher_agent.py` Reports `No pending tasks`

### Cause

The agent is running correctly, but the Render backend does not currently have content marked as pending for publishing.

Publishing tasks are created by the backend workflow:

1. A user generates content in the GEO frontend.
2. The user clicks Publish.
3. The backend changes the content publish status to pending.
4. The local publisher agent polls the backend.
5. The agent publishes the pending item and reports the published URL.

### Fix

Create a pending task from the frontend:

1. Open the GEO frontend on Vercel.
2. Generate a GEO content package.
3. Click Publish on the content item.
4. Watch the publisher agent terminal.

Expected terminal output after a task is available:

```text
Publishing content <id>
Published successfully
```

If the agent still reports no pending tasks, confirm that `publisher_agent.py` points to the correct Render backend URL.

## Issue: Render Backend Works but Reddit Publishing Does Not

### Cause

This is expected if the local publisher agent is not running. Render hosts the backend API, but Reddit publishing occurs on the local Mac or Mac Mini through Playwright.

Render does not store `reddit_state.json`, does not log in to Reddit, and does not run the browser-based publisher.

### Fix

Start the publisher agent locally:

```bash
cd /path/to/geo-engine/backend
source venv/bin/activate
python publisher_agent.py
```

Confirm these local files exist:

```bash
ls -l publisher_agent.py
ls -l save_reddit_state.py
ls -l reddit_state.json
```

If `reddit_state.json` is missing or expired, regenerate it:

```bash
python save_reddit_state.py
```

Then start the agent again:

```bash
python publisher_agent.py
```

## Issue: `reddit_state.json` Was Accidentally Added to Git

### Cause

The authentication state file was generated before the ignore rule was added, or it was force-added manually.

### Fix

Remove it from Git tracking while keeping the local file on disk:

```bash
cd /path/to/geo-engine
git rm --cached backend/reddit_state.json
git commit -m "Stop tracking local Reddit authentication state"
```

Confirm it is ignored:

```bash
git status --short
```

The file should not appear as staged or modified.
