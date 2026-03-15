#!/bin/sh

set -eu

mkdir -p /backend/staticfiles
chmod -R u+rwX /backend/staticfiles || true

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

exec daphne -b 0.0.0.0 -p 8000 src.asgi:application
