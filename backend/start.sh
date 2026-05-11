#!/bin/bash
set -e

# If Render (or any PaaS) provides a single DATABASE_URL, parse it into
# individual POSTGRES_* vars that Liquibase needs.
if [ -n "${DATABASE_URL}" ]; then
  eval "$(python3 -c "
from urllib.parse import urlparse
import os
u = urlparse(os.environ['DATABASE_URL'])
print('POSTGRES_HOST=' + (u.hostname or 'localhost'))
print('POSTGRES_PORT=' + str(u.port or 5432))
print('POSTGRES_USER=' + (u.username or 'asvs'))
print('POSTGRES_PASSWORD=' + (u.password or ''))
print('POSTGRES_DB=' + (u.path.lstrip('/') or 'asvs'))
")"
fi

echo "==> Running database migrations..."
liquibase \
  --url="jdbc:postgresql://${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-asvs}" \
  --username="${POSTGRES_USER:-asvs}" \
  --password="${POSTGRES_PASSWORD}" \
  --changeLogFile="db/changelog/db.changelog-root.yaml" \
  update

echo "==> Migrations complete. Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
