#!/usr/bin/env bash

set -euo pipefail

DB_HOST="${LOCAL_DB_HOST:-127.0.0.1}"
DB_PORT="${LOCAL_DB_PORT:-5432}"
DB_NAME="${LOCAL_DB_NAME:-geo_engine}"
DB_USER="${LOCAL_DB_USER:-geo_user}"
DB_PASSWORD="${LOCAL_DB_PASSWORD:-geo_password}"

if ! command -v psql >/dev/null 2>&1; then
  echo "PostgreSQL client tools are missing. Install PostgreSQL 16 with:"
  echo "  brew install postgresql@16"
  exit 1
fi

if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Starting PostgreSQL 16..."
    brew services start postgresql@16
  else
    echo "PostgreSQL is not reachable at $DB_HOST:$DB_PORT."
    exit 1
  fi
fi

for _ in {1..30}; do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready at $DB_HOST:$DB_PORT."
  exit 1
fi

if ! psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -Atqc \
  "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -q 1; then
  echo "Creating PostgreSQL role $DB_USER..."
  psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'"
fi

if ! psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -Atqc \
  "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
  echo "Creating PostgreSQL database $DB_NAME..."
  createdb -h "$DB_HOST" -p "$DB_PORT" -O "$DB_USER" "$DB_NAME"
fi

psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -v ON_ERROR_STOP=1 \
  -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER" >/dev/null

echo "Local PostgreSQL is ready: $DB_NAME owned by $DB_USER at $DB_HOST:$DB_PORT"
