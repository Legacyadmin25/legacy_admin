# Legacy Admin cPanel Deployment

This guide is for the CyberCircuit cPanel shared-hosting deployment using the Python Application feature and Passenger.

## Files used for cPanel

- `passenger_wsgi.py`
- `requirements-cpanel.txt`
- `legacyadmin/settings.py`

## cPanel application values

- Python version: `3.12.11`
- Application root: `legacyadmin_app`
- Application URL: `legacyadmin.co.za`
- Application startup file: `passenger_wsgi.py`
- Application entry point: `application`

## Required cPanel environment variables

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=legacyadmin.co.za,www.legacyadmin.co.za`
- `FIELD_ENCRYPTION_KEY`
- `DB_ENGINE=django.db.backends.mysql`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST=localhost`
- `DB_PORT=3306`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000`

Optional feature variables:

- `OPENAI_API_KEY`
- `DEFAULT_OPENAI_MODEL`
- `BULKSMS_API_TOKEN`
- `BULKSMS_USERNAME`
- `BULKSMS_PASSWORD`
- `EASYPAY_API_KEY`

## Deploy from GitHub over SSH

SSH into the server and activate the cPanel virtual environment using the command shown on the Python Application page.

Example:

```bash
source /home1/legacybi/virtualenv/legacyadmin_app/3.12/bin/activate && cd /home1/legacybi/legacyadmin_app
```

If the directory is empty, clone the repository:

```bash
git clone https://github.com/Legacyadmin25/legacy_admin.git .
```

If the directory already contains the repository:

```bash
git pull origin main
```

## Install dependencies

Use the cPanel-specific requirements file instead of the UTF-16 `requirements.txt`.

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-cpanel.txt
```

## First-time Django setup

Run these from `/home1/legacybi/legacyadmin_app` with the virtualenv active:

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

## Restart the app

Use the cPanel Python Application screen and click `Restart`.

## Expected shared-hosting limitations

- `WeasyPrint` may fail if the server does not have the required system libraries.
- `pytesseract` requires the Tesseract binary on the server.
- Celery workers are not expected to run continuously on shared hosting.

The codebase was updated so missing PDF/OCR libraries should no longer prevent the main Django app from starting. Those specific features may still return runtime errors until the host provides the native dependencies.