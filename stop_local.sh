#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.local"

stop_process() {
  local name="$1"
  local pid_file="$RUNTIME_DIR/$name.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not recorded as running."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped $name (PID $pid)."
  else
    echo "$name was not running (stale PID $pid)."
  fi

  rm -f "$pid_file"
}

stop_process backend
stop_process frontend

if [[ "${1:-}" == "--postgres" ]]; then
  brew services stop postgresql@16
  echo "Stopped PostgreSQL 16."
else
  echo "PostgreSQL remains running. Use ./stop_local.sh --postgres to stop it too."
fi
