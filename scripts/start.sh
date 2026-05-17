#!/bin/bash
set -e

echo "--- Starting Gunicorn ---"
echo "Settings: $DJANGO_SETTINGS_MODULE | Port: ${PORT:-8000}"
PORT="${PORT:-8000}"
exec gunicorn terratrail.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 3 \
  --threads 2 \
  --timeout 120 \
  --log-file -
