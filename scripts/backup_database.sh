#!/bin/bash
# Database backup script for Legacy Admin
# This script creates a backup of the PostgreSQL database and uploads it to S3

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
BACKUP_DIR="/tmp/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILENAME="legacyadmin_backup_${DATE}.sql.gz"
FULL_BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
S3_BUCKET="${AWS_STORAGE_BUCKET_NAME:-legacyadmin-backups}"
S3_PREFIX="database-backups"
RETENTION_DAYS=30
LOG_FILE="/var/log/legacyadmin/backups.log"

# Ensure backup directory exists
mkdir -p ${BACKUP_DIR}

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

log "Starting database backup"

# Check required environment variables
if [ -z "${DB_NAME}" ] || [ -z "${DB_USER}" ] || [ -z "${DB_PASSWORD}" ] || [ -z "${DB_HOST}" ]; then
    log "ERROR: Database environment variables are not set"
    exit 1
fi

# Create backup
log "Creating backup of ${DB_NAME} database"
PGPASSWORD="${DB_PASSWORD}" pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -F p | gzip > ${FULL_BACKUP_PATH}

# Check if backup was successful
if [ $? -ne 0 ]; then
    log "ERROR: Database backup failed"
    exit 1
fi

# Get backup size
BACKUP_SIZE=$(du -h ${FULL_BACKUP_PATH} | cut -f1)
log "Backup created successfully: ${FULL_BACKUP_PATH} (${BACKUP_SIZE})"

# Upload to S3 if AWS credentials are set
if [ -n "${AWS_ACCESS_KEY_ID}" ] && [ -n "${AWS_SECRET_ACCESS_KEY}" ]; then
    log "Uploading backup to S3 bucket: ${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILENAME}"
    aws s3 cp ${FULL_BACKUP_PATH} s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILENAME}
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to upload backup to S3"
        exit 1
    fi
    
    log "Backup uploaded to S3 successfully"
    
    # Clean up old backups in S3
    log "Cleaning up backups older than ${RETENTION_DAYS} days from S3"
    OLD_BACKUPS=$(aws s3 ls s3://${S3_BUCKET}/${S3_PREFIX}/ | grep -E "legacyadmin_backup_" | awk '{print $4}' | sort | head -n -${RETENTION_DAYS})
    
    for backup in ${OLD_BACKUPS}; do
        log "Deleting old backup: s3://${S3_BUCKET}/${S3_PREFIX}/${backup}"
        aws s3 rm s3://${S3_BUCKET}/${S3_PREFIX}/${backup}
    done
else
    log "WARNING: AWS credentials not set, skipping S3 upload"
fi

# Clean up local backup
log "Cleaning up local backup file"
rm ${FULL_BACKUP_PATH}

log "Backup process completed successfully"
