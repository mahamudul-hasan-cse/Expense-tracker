#!/bin/sh
# Apply database migrations, then start the API.
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Applying database migrations..."
  # One instance at a time: Postgres advisory lock (only matters with several replicas)
  python -m app.migrate
fi

# Rate limits and logs get the client IP from the frontend proxy (X-Client-IP + secret,
# see app/client_ip.py), so uvicorn's own proxy-header handling stays at its default.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --no-access-log \
  --timeout-graceful-shutdown 20
