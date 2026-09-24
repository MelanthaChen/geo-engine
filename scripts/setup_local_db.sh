#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be supplied by backend/.env."
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "PostgreSQL client tools are missing. Install PostgreSQL 16 with:"
  echo "  brew install postgresql@16"
  exit 1
fi

for _ in {1..30}; do
  if pg_isready -d "$DATABASE_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! pg_isready -d "$DATABASE_URL" >/dev/null 2>&1; then
  echo "The PostgreSQL server configured by backend/.env is not reachable."
  echo "For the repository Docker database, run: docker compose up -d postgres"
  exit 1
fi

echo "The PostgreSQL server configured by backend/.env is ready."
