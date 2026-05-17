web: gunicorn terratrail.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-file -
worker: celery -A terratrail worker -l info
beat: celery -A terratrail beat -l info
