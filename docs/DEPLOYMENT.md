# Legacy Admin Deployment Guide

This document provides detailed instructions for deploying the Legacy Admin system to production environments.

## Prerequisites

Before deployment, ensure you have the following:

- Docker and Docker Compose installed on the deployment server
- Kubernetes cluster configured (if using Kubernetes deployment)
- Access to a PostgreSQL database server
- Redis server for caching and task queue
- Domain name configured with DNS records
- SSL certificates for HTTPS

## Environment Configuration

1. Create a `.env` file in the project root, using the `.env.template` as a reference:

```bash
cp .env.template .env
```

2. Edit the `.env` file and fill in all required environment variables for production:

```
# Database Settings
DB_NAME=legacyadmin_prod
DB_USER=dbuser
DB_PASSWORD=secure_password
DB_HOST=db.example.com
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://redis.example.com:6379/0

# Email Settings
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=admin@example.com
EMAIL_HOST_PASSWORD=email_password
DEFAULT_FROM_EMAIL=admin@example.com

# Security Settings
SECRET_KEY=your_very_secure_random_secret_key
ALLOWED_HOSTS=app.example.com,www.app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com,https://www.app.example.com

# Storage Settings
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=legacyadmin-prod
AWS_S3_REGION_NAME=us-east-1

# Sentry Error Tracking
SENTRY_DSN=https://your_sentry_dsn@o123456.ingest.sentry.io/project_id

# Application Settings
ENVIRONMENT=production
DEBUG=False
```

## Deployment Methods

There are three primary methods for deploying the application:

### 1. Docker Compose Deployment

Suitable for single-server setups or small deployments:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/legacyadmin.git
   cd legacyadmin
   ```

2. Create and configure the `.env` file as described above.

3. Build and start the containers:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. Collect static files:
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

6. Configure Nginx or a similar web server to proxy requests to the Docker containers.

### 2. Kubernetes Deployment

Recommended for larger, scalable deployments:

1. Create Kubernetes secrets for environment variables:
   ```bash
   # Create secrets from .env file
   kubectl create secret generic legacyadmin-secrets --from-env-file=.env
   
   # Create SSL secrets if not using a managed certificate
   kubectl create secret tls legacyadmin-tls --cert=path/to/cert.pem --key=path/to/key.pem
   ```

2. Apply the Kubernetes manifests:
   ```bash
   kubectl apply -f kubernetes/
   ```

3. Verify the deployment:
   ```bash
   kubectl get pods
   kubectl get services
   kubectl get ingress
   ```

4. Run database migrations:
   ```bash
   kubectl exec -it $(kubectl get pods -l app=legacyadmin-web -o jsonpath="{.items[0].metadata.name}") -- python manage.py migrate
   ```

### 3. CI/CD Pipeline Deployment

For automated deployments via GitHub Actions:

1. Set up the required secrets in your GitHub repository:
   - `DIGITALOCEAN_TOKEN`
   - `CLUSTER_NAME`
   - `SLACK_WEBHOOK_URL`

2. Push your code to the main or develop branch, or manually trigger the workflow.

3. Monitor the GitHub Actions workflow for deployment progress.

## Post-Deployment Tasks

After successful deployment, perform these tasks:

1. Verify the application is running correctly:
   ```bash
   curl -I https://app.example.com
   ```

2. Check logs for any errors:
   ```bash
   # Docker Compose
   docker-compose logs -f
   
   # Kubernetes
   kubectl logs -f deployment/legacyadmin-web
   kubectl logs -f deployment/legacyadmin-celery
   ```

3. Run the application health check:
   ```bash
   curl https://app.example.com/health/
   ```

## Backup and Restore

### Database Backup

Use the provided scripts for database backup:

```bash
# On the server
cd /path/to/legacyadmin
./scripts/backup_database.sh
```

### Database Restore

To restore from a backup:

```bash
cd /path/to/legacyadmin
./scripts/restore_database.sh legacyadmin_backup_YYYY-MM-DD_HH-MM-SS.sql.gz
```

## Monitoring

The application exposes the following monitoring endpoints:

- Health check: `/health/`
- Readiness probe: `/health/ready/`
- Liveness probe: `/health/live/`
- Prometheus metrics: `/metrics/`

Configure Prometheus to scrape the metrics endpoint for monitoring.

## Troubleshooting

Common issues and solutions:

### Database Connection Issues

If the application cannot connect to the database:

1. Check the database credentials in the `.env` file
2. Verify the database server is running and accessible
3. Check network connectivity between the application and database servers

### Static Files Not Loading

If static files are not being served correctly:

1. Ensure `collectstatic` was run
2. Check the storage settings in the `.env` file
3. Verify the S3 bucket permissions if using S3 storage

### Email Sending Failures

If emails are not being sent:

1. Check the email settings in the `.env` file
2. Verify the SMTP server is accessible
3. Test with a simpler SMTP server like MailHog for debugging

## Rollback Procedure

If a deployment fails, follow these steps to rollback:

### Docker Compose Rollback

```bash
# Get the previous image tag
docker-compose down
# Edit docker-compose.yml to use the previous image tag
docker-compose up -d
```

### Kubernetes Rollback

```bash
# Rollback to the previous deployment
kubectl rollout undo deployment/legacyadmin-web
kubectl rollout undo deployment/legacyadmin-celery
```

## Security Considerations

- Regularly update all dependencies
- Enable security headers via the security middleware
- Use strong, unique passwords for all services
- Implement IP restrictions for admin access
- Keep database backups encrypted
- Regularly audit user access and permissions

## Performance Tuning

For optimal performance:

1. Adjust Gunicorn worker count based on available CPU cores:
   ```
   GUNICORN_WORKERS=4*cpu_cores+1
   ```

2. Configure proper cache timeouts for different types of data
3. Monitor and optimize database queries
4. Use connection pooling for database connections
5. Implement CDN for static files
6. Set up Redis cache with appropriate memory limits
