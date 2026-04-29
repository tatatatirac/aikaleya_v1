#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/var/www/aikaleya"

cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
  cp .env.production.example .env
  echo "Created .env from .env.production.example. Edit it before continuing."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python backend/manage.py migrate
python backend/manage.py check --deploy
python backend/manage.py production_check
python backend/manage.py collectstatic --noinput
python backend/manage.py backup_data

echo "Kaleya bootstrap completed. Create superuser if needed:"
echo "source .venv/bin/activate && python backend/manage.py createsuperuser"
