#!/bin/bash
# Database restore script for Legacy Admin
# This script restores a PostgreSQL database from a backup (local or S3)

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
BACKUP_DIR="/tmp/backups"
S3_BUCKET="${AWS_STORAGE_BUCKET_NAME:-legacyadmin-backups}"
S3_PREFIX="database-backups"
LOG_FILE="/var/log/legacyadmin/backups.log"

# Ensure backup directory exists
mkdir -p ${BACKUP_DIR}

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# Check if backup file is provided
if [ -z "$1" ]; then
    log "ERROR: No backup file specified. Usage: $0 <backup_filename> [--list-only] [--from-s3]"
    exit 1
fi

BACKUP_FILENAME="$1"
LIST_ONLY=false
FROM_S3=false

# Parse additional arguments
shift
while [ "$1" != "" ]; do
    case $1 in
        --list-only )   LIST_ONLY=true
                        ;;
        --from-s3 )     FROM_S3=true
                        ;;
        * )             log "ERROR: Unknown parameter: $1"
                        exit 1
    esac
    shift
done

# If --list-only flag is provided, list available backups and exit
if [ "$LIST_ONLY" = true ]; then
    if [ "$FROM_S3" = true ]; then
        if [ -z "${AWS_ACCESS_KEY_ID}" ] || [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
            log "ERROR: AWS credentials not set"
            exit 1
        fi
        log "Listing backups from S3 bucket: ${S3_BUCKET}/${S3_PREFIX}/"
        aws s3 ls s3://${S3_BUCKET}/${S3_PREFIX}/ | grep -E "legacyadmin_backup_"
    else
        log "Listing local backups in ${BACKUP_DIR}:"
        ls -la ${BACKUP_DIR} | grep -E "legacyadmin_backup_"
    fi
    exit 0
fi

# Full path to the backup file
FULL_BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# Check required environment variables
if [ -z "${DB_NAME}" ] || [ -z "${DB_USER}" ] || [ -z "${DB_PASSWORD}" ] || [ -z "${DB_HOST}" ]; then
    log "ERROR: Database environment variables are not set"
    exit 1
fi

# Download from S3 if requested
if [ "$FROM_S3" = true ]; then
    if [ -z "${AWS_ACCESS_KEY_ID}" ] || [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
        log "ERROR: AWS credentials not set"
        exit 1
    fi
    
    log "Downloading backup from S3: s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILENAME}"
    aws s3 cp s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILENAME} ${FULL_BACKUP_PATH}
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to download backup from S3"
        exit 1
    fi
    
    log "Backup downloaded from S3 successfully"
else
    # Check if the local backup file exists
    if [ ! -f ${FULL_BACKUP_PATH} ]; then
        log "ERROR: Backup file not found: ${FULL_BACKUP_PATH}"
        exit 1
    fi
fi

# Ask for confirmation before restoring the database
read -p "Are you sure you want to restore the database? This will OVERWRITE the current database! (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log "Database restore aborted by user"
    exit 0
fi

log "Starting database restore process"

# Create a temporary database connection string
DB_CONNECTION="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-5432}/${DB_NAME}"

# Check if we can connect to the database
log "Checking database connection"
if ! PGPASSWORD="${DB_PASSWORD}" psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1;" > /dev/null 2>&1; then
    log "ERROR: Cannot connect to the database"
    exit 1
fi

# Backup filename pattern check - should be .sql.gz
if [[ ${BACKUP_FILENAME} == *.sql.gz ]]; then
    log "Restoring compressed SQL backup: ${FULL_BACKUP_PATH}"
    gunzip -c ${FULL_BACKUP_PATH} | PGPASSWORD="${DB_PASSWORD}" psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME}
elif [[ ${BACKUP_FILENAME} == *.sql ]]; then
    log "Restoring uncompressed SQL backup: ${FULL_BACKUP_PATH}"
    PGPASSWORD="${DB_PASSWORD}" psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} < ${FULL_BACKUP_PATH}
else
    log "ERROR: Unsupported backup format. Expecting .sql or .sql.gz file"
    exit 1
fi

# Check if restore was successful
if [ $? -ne 0 ]; then
    log "ERROR: Database restore failed"
    exit 1
fi

log "Database restore completed successfully"

# Clean up downloaded backup if it was from S3
if [ "$FROM_S3" = true ]; then
    log "Cleaning up downloaded backup file"
    rm ${FULL_BACKUP_PATH}
fi
