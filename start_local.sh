#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.local"
ENV_FILE="$BACKEND_DIR/.env.local"
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"

mkdir -p "$RUNTIME_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$BACKEND_DIR/.env.local.example" "$ENV_FILE"
  echo "Created $ENV_FILE from the local example."
fi

set -a
source "$ENV_FILE"
set +a

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Backend virtual environment is missing. Run:"
  echo "  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv backend/venv"
  echo "  backend/venv/bin/python -m pip install -r backend/requirements.txt"
  exit 1
fi

"$ROOT_DIR/scripts/setup_local_db.sh"

echo "Applying Alembic migrations..."
(
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m alembic upgrade head
)

start_process() {
  local name="$1"
  local pid_file="$RUNTIME_DIR/$name.pid"
  local log_file="$RUNTIME_DIR/$name.log"
  shift

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name is already running (PID $(cat "$pid_file"))."
    return
  fi

  nohup "$@" >"$log_file" 2>&1 </dev/null &
  echo $! >"$pid_file"
  echo "Started $name (PID $!, log: $log_file)."
}

start_process backend bash -c \
  "cd '$BACKEND_DIR' && exec '$PYTHON_BIN' -m uvicorn main:app --host 127.0.0.1 --port 8000"

start_process frontend bash -c \
  "cd '$FRONTEND_DIR' && exec env VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1"

echo "Waiting for the backend..."
for _ in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl --silent --fail http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "Backend did not become healthy. Inspect $RUNTIME_DIR/backend.log"
  exit 1
fi

echo
echo "Local GEO Engine is ready:"
echo "  Frontend: http://127.0.0.1:5173"
echo "  Backend:  http://127.0.0.1:8000"
echo "  API docs: http://127.0.0.1:8000/docs"
echo
echo "Run local agents in separate terminals:"
echo "  cd '$BACKEND_DIR' && source venv/bin/activate && set -a && source .env.local && set +a && python -u publisher_agent.py"
echo "  cd '$BACKEND_DIR' && source venv/bin/activate && set -a && source .env.local && set +a && python -u retriever_agent.py"
echo
echo "Stop backend/frontend with: ./stop_local.sh"
