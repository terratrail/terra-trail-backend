# ========================================================
# Dockerfile for TerraTrail SaaS Backend
# ========================================================

# Start from the official lightweight Python image
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=terratrail.settings \
    DEBUG=False

# Create and set the working directory
WORKDIR /app

# Install system dependencies (needed for PostgreSQL, caching, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Collect static files — use base settings so no external services
RUN python manage.py collectstatic --noinput
# (S3, PostgreSQL) are required at build time.
# RUN DJANGO_SETTINGS_MODULE=terratrail.settings.base python manage.py collectstatic --noinput

# Expose the port Gunicorn will run on
EXPOSE 8000

# Create a non-root user for better security
RUN useradd -m terratrailuser
RUN chown -R terratrailuser:terratrailuser /app
USER terratrailuser

# Make the start script executable
RUN chmod +x /app/scripts/start.sh

# Start the application via the start script
CMD ["/app/scripts/start.sh"]
