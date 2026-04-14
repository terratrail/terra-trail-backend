web: gunicorn terratrail.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A terratrail worker -l info
beat: celery -A terratrail beat -l info
release: python manage.py migrate --noinput
