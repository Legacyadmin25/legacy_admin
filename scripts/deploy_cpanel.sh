#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/home1/legacybi/legacyadmin_app}"
VENV_ACTIVATE="${VENV_ACTIVATE:-/home1/legacybi/virtualenv/legacyadmin_app/3.12/bin/activate}"
BRANCH="${BRANCH:-main}"

if [ ! -d "$APP_ROOT" ]; then
  echo "Application root not found: $APP_ROOT" >&2
  exit 1
fi

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "Virtualenv activate script not found: $VENV_ACTIVATE" >&2
  exit 1
fi

source "$VENV_ACTIVATE"
cd "$APP_ROOT"

echo "Using app root: $APP_ROOT"
echo "Using branch: $BRANCH"

git status --short
git pull origin "$BRANCH"

pip install --upgrade pip setuptools wheel
pip install -r requirements-cpanel.txt

python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput

if [ -d tmp ]; then
  mkdir -p tmp
  touch tmp/restart.txt
  echo "Passenger restart requested via tmp/restart.txt"
else
  echo "tmp directory not found. Restart the Python app from cPanel if needed."
fi

echo "Deployment complete. Verify the sidebar shows Build workspace-reporthub-20260409"