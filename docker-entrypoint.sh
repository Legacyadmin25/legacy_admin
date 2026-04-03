#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
import psycopg2
import os

host = os.environ.get('DB_HOST', 'db')
port = os.environ.get('DB_PORT', '5432')
dbname = os.environ.get('DB_NAME', 'postgres')
user = os.environ.get('DB_USER', 'postgres')
password = os.environ.get('DB_PASSWORD', 'postgres')

while True:
    try:
        conn = psycopg2.connect(f'dbname={dbname} user={user} password={password} host={host} port={port}')
        conn.close()
        break
    except psycopg2.OperationalError:
        print('Database not ready yet. Waiting...')
        time.sleep(1)
"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if needed
python -c "
import os
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
DJANGO_SUPERUSER_USERNAME = os.environ.get('DJANGO_SUPERUSER_USERNAME')
DJANGO_SUPERUSER_EMAIL = os.environ.get('DJANGO_SUPERUSER_EMAIL')
DJANGO_SUPERUSER_PASSWORD = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD:
    try:
        if not User.objects.filter(username=DJANGO_SUPERUSER_USERNAME).exists():
            User.objects.create_superuser(
                username=DJANGO_SUPERUSER_USERNAME,
                email=DJANGO_SUPERUSER_EMAIL,
                password=DJANGO_SUPERUSER_PASSWORD
            )
            print('Superuser created.')
        else:
            print('Superuser already exists.')
    except Exception as e:
        print(f'Error creating superuser: {e}')
"

# Start the server
exec "$@"
