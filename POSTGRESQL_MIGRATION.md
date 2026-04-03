# PostgreSQL Migration Guide

## Overview
This guide walks through migrating from SQLite to PostgreSQL for production use.

**Why PostgreSQL?**
- SQLite cannot handle concurrent writes safely
- PostgreSQL supports full ACID transactions
- Better for multi-user environments
- Essential for scaling beyond 1-2 users

## Prerequisites

### Option A: PostgreSQL Server (Recommended for Production)
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# macOS: brew install postgresql@15
# Linux: sudo apt-get install postgresql postgresql-contrib
```

### Option B: Docker (Recommended for Development/Testing)
```bash
# Pull PostgreSQL image
docker pull postgres:15

# Run PostgreSQL container
docker run --name legacyadmin-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=secure_password_here \
  -e POSTGRES_DB=legacyadmin \
  -p 5432:5432 \
  -d postgres:15
```

## Step 1: Backup Current SQLite Database

```bash
# Copy the current SQLite database
cp db.sqlite3 db.sqlite3.backup
```

## Step 2: Install psycopg2

```bash
# Already installed:
pip install psycopg2-binary
```

## Step 3: Create PostgreSQL Database

```bash
# Using psql (PostgreSQL command-line tool)
psql -U postgres

# In psql:
CREATE DATABASE legacyadmin;
\l  # List databases to verify
\q  # Quit
```

## Step 4: Configure .env for PostgreSQL

Add or update these variables in your `.env` file:

```env
# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=legacyadmin
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432
```

## Step 5: Export SQLite Data

```bash
# Dump SQLite data as JSON fixtures
python manage.py dumpdata --indent=2 > fixtures/full_dump.json
```

## Step 6: Apply Migrations to PostgreSQL

```bash
# Run migrations on PostgreSQL
python manage.py migrate --skip-checks
```

## Step 7: Load Data from SQLite

```bash
# Load the JSON fixture into PostgreSQL
python manage.py loaddata fixtures/full_dump.json
```

## Step 8: Verify Migration

```bash
# Check record counts in PostgreSQL
python manage.py shell

# In Django shell:
from members.models import Member, Policy
from accounts.models import User

print(f"Users: {User.objects.count()}")
print(f"Members: {Member.objects.count()}")
print(f"Policies: {Policy.objects.count()}")
```

## Troubleshooting

### "Role doesn't exist" Error
PostgreSQL can't find the database role. Create it:
```bash
createuser -U postgres legacyadmin
```

### "Password authentication failed"
Verify credentials in .env match your PostgreSQL setup:
```bash
psql -U postgres -h localhost
```

### "Could not connect to server"
Ensure PostgreSQL is running:
```bash
# Check if PostgreSQL service is running
# Windows: Services > PostgreSQL
# macOS: brew services list
# Linux: sudo systemctl status postgresql
```

### Connection Timeout
If using Docker or remote server:
- Verify HOST and PORT in .env are correct
- Check firewall allows connections on port 5432
- Ensure PostgreSQL is configured to accept remote connections

## Rollback to SQLite (if needed)

```bash
# Revert .env to SQLite
DB_ENGINE=django.db.backends.sqlite3

# Django will use db.sqlite3 again
```

## Notes

- **Backup Location**: Full backup is at `db.sqlite3.backup`
- **JSON Dump**: Available at `fixtures/full_dump.json` if migration fails
- **Zero Downtime**: Migration can be done during off-hours
- **Testing**: Test migration in development environment first

## Performance Tips

After migration, consider:

1. Create indexes on frequently queried fields
2. Run ANALYZE to update query planner
3. Configure connection pooling (pgBouncer)
4. Enable compression for backups

```sql
-- Run in PostgreSQL
ANALYZE;
```

## Next Steps

- Set up automated backups with pg_dump
- Configure replication for high availability
- Monitor database performance with pg_stat_statements
- Schedule regular VACUUM ANALYZE runs
