#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "==> Installing dependencies..."
pip install -r ../requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Build complete!"
