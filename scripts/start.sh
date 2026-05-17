#!/bin/bash

# ========================================================
# Start script for TerraTrail SaaS Backend
# ========================================================

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- Starting Environment Debug ---"
echo "Available Env keys: $(env | cut -d= -f1 | sort | tr '\n' ' ')"
echo "---------------------------------"

echo "--- Using Settings: $DJANGO_SETTINGS_MODULE ---"

echo "--- Generating Migrations (In case of missing files) ---"
python manage.py makemigrations --noinput

echo "--- Running Migrations ---"
python manage.py migrate --noinput

echo "--- Creating Superuser (if credentials provided) ---"
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || echo "Superuser already exists or creation skipped."
else
  echo "DJANGO_SUPERUSER_* env vars not set — skipping superuser creation."
fi

echo "--- Starting Gunicorn ---"
# Default to port 8000 if PORT is not set
PORT="${PORT:-8000}"
gunicorn terratrail.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2
