#!/bin/bash
set -e

echo "==> Running database migrations..."
liquibase \
  --url="jdbc:postgresql://${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-asvs}" \
  --username="${POSTGRES_USER:-asvs}" \
  --password="${POSTGRES_PASSWORD}" \
  --changeLogFile="db/changelog/db.changelog-root.yaml" \
  update

echo "==> Migrations complete. Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
