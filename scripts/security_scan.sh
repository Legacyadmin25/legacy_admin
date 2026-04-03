#!/bin/bash
# Security verification script for Legacy Admin
# This script runs basic security checks against a deployed environment

set -e

# Configuration
TARGET_URL=${1:-"https://staging.legacyadmin.example.com"}
OUTPUT_DIR="./security_reports"
DATE=$(date +%Y-%m-%d)
REPORT_FILE="${OUTPUT_DIR}/security_scan_${DATE}.txt"

# Create output directory
mkdir -p ${OUTPUT_DIR}

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a ${REPORT_FILE}
}

log "Starting security scan for ${TARGET_URL}"

# Check if required tools are installed
for tool in nmap nikto sslyze; do
    if ! command -v ${tool} &> /dev/null; then
        log "ERROR: ${tool} is not installed. Please install it to continue."
        exit 1
    fi
done

# 1. Basic port scan
log "Running port scan..."
nmap -sV -T4 --script vuln $(echo ${TARGET_URL} | sed 's|https\?://||' | cut -d/ -f1) -oN "${OUTPUT_DIR}/nmap_${DATE}.txt"
log "Port scan completed. Results saved to ${OUTPUT_DIR}/nmap_${DATE}.txt"

# 2. Web vulnerability scan with Nikto
log "Running web vulnerability scan..."
nikto -h ${TARGET_URL} -o "${OUTPUT_DIR}/nikto_${DATE}.txt"
log "Web vulnerability scan completed. Results saved to ${OUTPUT_DIR}/nikto_${DATE}.txt"

# 3. SSL/TLS configuration check
log "Checking SSL/TLS configuration..."
sslyze --regular $(echo ${TARGET_URL} | sed 's|https\?://||' | cut -d/ -f1) > "${OUTPUT_DIR}/sslyze_${DATE}.txt"
log "SSL/TLS check completed. Results saved to ${OUTPUT_DIR}/sslyze_${DATE}.txt"

# 4. Security headers check
log "Checking security headers..."
curl -s -I ${TARGET_URL} > "${OUTPUT_DIR}/headers_${DATE}.txt"
log "Headers check completed. Results saved to ${OUTPUT_DIR}/headers_${DATE}.txt"

# 5. Check for common security misconfigurations
log "Checking for common security misconfigurations..."

# Check for directory listing
curl -s ${TARGET_URL}/static/ | grep -q "Index of" && \
    log "WARNING: Directory listing is enabled for /static/" || \
    log "OK: Directory listing is disabled for /static/"

# Check for admin accessibility
curl -s -o /dev/null -w "%{http_code}" ${TARGET_URL}/admin/ | grep -q "200" && \
    log "WARNING: Admin interface is publicly accessible" || \
    log "OK: Admin interface is not directly accessible"

# Check for robots.txt
curl -s -o /dev/null -w "%{http_code}" ${TARGET_URL}/robots.txt | grep -q "200" || \
    log "WARNING: No robots.txt file found"

# Check for error disclosure
curl -s -o /dev/null -w "%{http_code}" ${TARGET_URL}/nonexistent-page-12345 | grep -q "500" && \
    log "WARNING: Server might be disclosing error details" || \
    log "OK: Error handling seems appropriate"

# 6. Rate limiting test
log "Testing rate limiting..."
for i in {1..20}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${TARGET_URL}/accounts/login/)
    log "Request $i: Status code $STATUS"
    if [[ "$STATUS" == "429" ]]; then
        log "OK: Rate limiting is working (triggered after $i requests)"
        break
    fi
    if [[ $i == 20 ]]; then
        log "WARNING: Rate limiting not triggered after 20 requests"
    fi
done

# 7. CSRF protection test
log "Testing CSRF protection..."
CSRF_STATUS=$(curl -s -X POST -o /dev/null -w "%{http_code}" ${TARGET_URL}/accounts/login/)
if [[ "$CSRF_STATUS" == "403" ]]; then
    log "OK: CSRF protection is working"
else
    log "WARNING: CSRF protection might not be properly enforced"
fi

# Summarize findings
log "Security scan completed. Please review the reports in ${OUTPUT_DIR} for detailed findings."
log "Remember this is a basic scan and not a replacement for a professional penetration test."
log "==== NEXT STEPS ===="
log "1. Review all warnings and fix identified issues"
log "2. Consider a professional penetration test before production launch"
log "3. Implement regular security scanning as part of your CI/CD pipeline"
