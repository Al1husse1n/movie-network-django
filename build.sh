#!/usr/bin/env bash
# Build script for Render deployment.
# Runs on every deploy before the service starts.
set -o errexit  # exit on any command failure

echo "=== Upgrading pip ==="
pip install --upgrade pip

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Build complete ==="
