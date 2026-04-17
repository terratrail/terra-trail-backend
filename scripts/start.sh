#!/bin/bash

# ========================================================
# Start script for TerraTrail SaaS Backend
# ========================================================

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- Running Migrations ---"
python manage.py migrate --noinput

echo "--- Creating Superuser ---"
# This will use DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD
# We catch the error in case the superuser already exists
python manage.py createsuperuser --noinput || echo "Superuser creation failed or already exists"

echo "--- Starting Gunicorn ---"
# Default to port 8000 if PORT is not set
PORT="${PORT:-8000}"
gunicorn terratrail.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2
