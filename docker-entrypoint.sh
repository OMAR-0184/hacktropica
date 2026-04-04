#!/bin/bash
set -e

if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
else
  echo "Alembic config not found, skipping migrations."
fi

echo "Starting application..."
exec "$@"
