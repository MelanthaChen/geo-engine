#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env.local"
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
DB_HOST="${LOCAL_DB_HOST:-127.0.0.1}"
DB_PORT="${LOCAL_DB_PORT:-5432}"
DB_NAME="${LOCAL_DB_NAME:-geo_engine}"
DB_USER="${LOCAL_DB_USER:-geo_user}"

if [[ "${1:-}" != "--yes" ]]; then
  echo "This deletes all data in the local database '$DB_NAME'."
  read -r -p "Type RESET to continue: " confirmation
  if [[ "$confirmation" != "RESET" ]]; then
    echo "Reset cancelled."
    exit 1
  fi
fi

set -a
source "$ENV_FILE"
set +a

dropdb -h "$DB_HOST" -p "$DB_PORT" --if-exists "$DB_NAME"
createdb -h "$DB_HOST" -p "$DB_PORT" -O "$DB_USER" "$DB_NAME"

(
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m alembic upgrade head
)

echo "Local database reset, migrated, and ready. The backend seeds the default Property on startup."
