#!/bin/bash

echo "Running database migrations..."
python migrate.py || echo "Migration failed or already applied, continuing..."

echo "Starting application..."
exec "$@"
