#!/bin/bash

echo "Running database migrations..."
alembic upgrade head || echo "Migration failed or already applied, continuing..."

echo "Starting application..."
exec "$@"
