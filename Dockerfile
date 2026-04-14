# ========================================================
# Dockerfile for TerraTrail SaaS Backend
# ========================================================

# Start from the official lightweight Python image
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=terratrail.settings.production

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

# Collect static files for production
RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn will run on
EXPOSE 8000

# Create a non-root user for better security
RUN useradd -m terratrailuser
RUN chown -R terratrailuser:terratrailuser /app
USER terratrailuser

# Start the application using Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "terratrail.wsgi:application"]
