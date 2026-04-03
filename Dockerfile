# Multi-stage Dockerfile for Legacy Admin

# Stage 1: Build dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .

# Install Python dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime image
FROM python:3.10-slim

# Create a non-root user
RUN useradd -m legacyuser

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R legacyuser:legacyuser /app
USER legacyuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=legacyadmin.settings_prod

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Use script to run application
COPY ./docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
