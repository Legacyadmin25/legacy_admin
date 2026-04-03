#!/bin/bash
# Disaster Recovery Test Script for Legacy Admin
# This script simulates disaster scenarios and tests recovery procedures

set -e

# Configuration
TEST_ENV=${1:-"staging"}
BACKUP_FILE=${2:-""}  # Optional specific backup file to restore
LOG_FILE="./dr_test_$(date +%Y-%m-%d).log"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

log "Starting Disaster Recovery Test in ${TEST_ENV} environment"

# Test 1: Database Restore
test_database_restore() {
    log "=== Test 1: Database Restore Test ==="
    
    # Create a test table and data to verify after restore
    log "Creating test marker in database..."
    kubectl exec -it deployment/legacyadmin-web -- python -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('CREATE TABLE IF NOT EXISTS dr_test (test_id serial PRIMARY KEY, test_date timestamp DEFAULT CURRENT_TIMESTAMP, test_value varchar(255))')
    cursor.execute(\"INSERT INTO dr_test (test_value) VALUES ('DR_TEST_MARKER_$(date +%s}')\")
    cursor.execute('SELECT * FROM dr_test ORDER BY test_id DESC LIMIT 1')
    row = cursor.fetchone()
    print(f'Created test marker: {row}')
"
    
    # Create a fresh backup
    log "Creating a fresh backup for testing..."
    if [[ -z "${BACKUP_FILE}" ]]; then
        kubectl exec -it deployment/legacyadmin-web -- ./scripts/backup_database.sh
        
        # Get the latest backup file
        BACKUP_FILE=$(kubectl exec -it deployment/legacyadmin-web -- ls -t /tmp/backups/legacyadmin_backup_* | head -1)
        log "Using latest backup: ${BACKUP_FILE}"
    else
        log "Using specified backup: ${BACKUP_FILE}"
    fi
    
    # Create a test database for restore
    log "Creating test database for restore..."
    kubectl exec -it deployment/legacyadmin-web -- python -c "
from django.db import connections
with connections['default'].cursor() as cursor:
    cursor.execute('CREATE DATABASE legacyadmin_dr_test')
"
    
    # Modify the DB_NAME env var temporarily for restore
    log "Setting up environment for test restore..."
    kubectl set env deployment/legacyadmin-web DB_NAME_ORIG=\${DB_NAME} DB_NAME=legacyadmin_dr_test
    
    # Wait for the environment change to propagate
    sleep 10
    
    # Test restore
    log "Performing test restore to separate database..."
    kubectl exec -it deployment/legacyadmin-web -- ./scripts/restore_database.sh ${BACKUP_FILE}
    
    # Verify the restored data
    log "Verifying restored data..."
    kubectl exec -it deployment/legacyadmin-web -- python -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT COUNT(*) FROM dr_test')
    count = cursor.fetchone()[0]
    print(f'Found {count} test markers in restored database')
    if count > 0:
        print('✅ Database restore test PASSED')
    else:
        print('❌ Database restore test FAILED - test markers not found')
        exit(1)
"
    
    # Cleanup - reset the environment
    log "Cleaning up after database restore test..."
    kubectl set env deployment/legacyadmin-web DB_NAME=\${DB_NAME_ORIG} DB_NAME_ORIG-
    
    # Drop the test database
    kubectl exec -it deployment/legacyadmin-web -- python -c "
from django.db import connections
with connections['default'].cursor() as cursor:
    cursor.execute('DROP DATABASE legacyadmin_dr_test')
"
    
    log "Database restore test completed successfully"
}

# Test 2: Redis Failure Simulation
test_redis_failure() {
    log "=== Test 2: Redis Failure Simulation ==="
    
    # Check if we have the Redis service
    if ! kubectl get service redis &>/dev/null; then
        log "Redis service not found in Kubernetes. Skipping Redis failure test."
        return
    }
    
    # Store the current Redis connection settings
    log "Storing current Redis settings..."
    REDIS_URL=$(kubectl get deployment legacyadmin-web -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="REDIS_URL")].value}')
    
    # Simulate Redis failure by changing the connection string to an invalid one
    log "Simulating Redis failure..."
    kubectl set env deployment/legacyadmin-web REDIS_URL=redis://nonexistent-redis:6379/0
    
    # Wait for the change to propagate
    sleep 10
    
    # Test application behavior without Redis
    log "Testing application behavior without Redis..."
    
    # Verify the application is still responsive
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${TEST_ENV}-legacyadmin)
    
    if [[ "${HTTP_STATUS}" == "200" || "${HTTP_STATUS}" == "302" ]]; then
        log "✅ Application is still responsive without Redis (Status: ${HTTP_STATUS})"
    else
        log "❌ Application is not responsive without Redis (Status: ${HTTP_STATUS})"
    fi
    
    # Check logs for graceful degradation
    log "Checking application logs for graceful degradation..."
    DEGRADATION_LOGS=$(kubectl logs deployment/legacyadmin-web --tail=50 | grep -i "redis.*fallback\|cache.*local\|degraded mode")
    
    if [[ -n "${DEGRADATION_LOGS}" ]]; then
        log "✅ Application shows signs of graceful degradation:"
        log "${DEGRADATION_LOGS}"
    else
        log "⚠️ No explicit signs of graceful degradation found in logs"
    fi
    
    # Restore the original Redis settings
    log "Restoring original Redis settings..."
    kubectl set env deployment/legacyadmin-web REDIS_URL=${REDIS_URL}
    
    # Wait for recovery
    sleep 10
    
    # Verify the application is back to normal
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${TEST_ENV}-legacyadmin)
    
    if [[ "${HTTP_STATUS}" == "200" || "${HTTP_STATUS}" == "302" ]]; then
        log "✅ Application recovered successfully after Redis restoration"
    else
        log "❌ Application did not recover properly after Redis restoration"
    fi
    
    log "Redis failure simulation test completed"
}

# Test 3: Celery Worker Failure Simulation
test_celery_failure() {
    log "=== Test 3: Celery Worker Failure Simulation ==="
    
    # Check if we have Celery workers
    if ! kubectl get deployment legacyadmin-celery &>/dev/null; then
        log "Celery deployment not found in Kubernetes. Skipping Celery failure test."
        return
    }
    
    # Record the current number of Celery worker replicas
    CELERY_REPLICAS=$(kubectl get deployment legacyadmin-celery -o jsonpath='{.spec.replicas}')
    log "Current Celery worker replicas: ${CELERY_REPLICAS}"
    
    # Simulate Celery failure by scaling down to 0
    log "Simulating Celery worker failure by scaling down to 0 replicas..."
    kubectl scale deployment legacyadmin-celery --replicas=0
    
    # Wait for scale down
    sleep 10
    
    # Check if the web application can still function
    log "Testing application behavior without Celery workers..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${TEST_ENV}-legacyadmin)
    
    if [[ "${HTTP_STATUS}" == "200" || "${HTTP_STATUS}" == "302" ]]; then
        log "✅ Application is still responsive without Celery workers (Status: ${HTTP_STATUS})"
    else
        log "❌ Application is not responsive without Celery workers (Status: ${HTTP_STATUS})"
    fi
    
    # Test submitting a task that would normally be processed by Celery
    log "Testing task submission without Celery workers..."
    TASK_RESULT=$(kubectl exec -it deployment/legacyadmin-web -- python -c "
from django.core.management import call_command
try:
    call_command('submit_test_task')
    print('Task submission handled gracefully')
except Exception as e:
    print(f'Task submission error: {str(e)}')
")
    
    log "Task submission result: ${TASK_RESULT}"
    
    # Restore Celery workers
    log "Restoring Celery workers..."
    kubectl scale deployment legacyadmin-celery --replicas=${CELERY_REPLICAS}
    
    # Wait for scale up
    sleep 30
    
    # Verify Celery is working again
    log "Verifying Celery functionality after restoration..."
    CELERY_STATUS=$(kubectl exec -it deployment/legacyadmin-web -- python -c "
from legacyadmin.celery import debug_task
result = debug_task.delay()
try:
    value = result.get(timeout=10)
    print(f'Celery is working: {value}')
    exit(0)
except Exception as e:
    print(f'Celery error: {str(e)}')
    exit(1)
")
    
    if [[ $? -eq 0 ]]; then
        log "✅ Celery functionality restored successfully"
    else
        log "❌ Celery functionality not restored properly"
    fi
    
    log "Celery failure simulation test completed"
}

# Run all tests
test_database_restore
test_redis_failure
test_celery_failure

log "All disaster recovery tests completed."
log "Please review the results and address any failures before production deployment."

# Output summary
PASSED=$(grep -c "✅" ${LOG_FILE})
FAILED=$(grep -c "❌" ${LOG_FILE})
WARNINGS=$(grep -c "⚠️" ${LOG_FILE})

log "=== Test Summary ==="
log "Tests passed: ${PASSED}"
log "Tests failed: ${FAILED}"
log "Warnings: ${WARNINGS}"

if [[ ${FAILED} -eq 0 ]]; then
    log "✅ OVERALL RESULT: PASSED"
    exit 0
else
    log "❌ OVERALL RESULT: FAILED - please review and fix issues"
    exit 1
fi
