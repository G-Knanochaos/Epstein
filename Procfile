web: sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn epstein_game.wsgi --bind 0.0.0.0:$PORT"
