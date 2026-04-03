#!/usr/bin/env python
"""
Phase 8: Credential Rotation - Testing Suite
Tests all rotated credentials and services
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
django.setup()

from django.conf import settings
from django.contrib.sessions.models import Session
from cryptography.fernet import Fernet
import requests

print("\n" + "="*80)
print("PHASE 8: CREDENTIAL ROTATION - TESTING SUITE")
print("="*80)

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Django SECRET_KEY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}TEST 1: Django SECRET_KEY{RESET}")
print("-" * 80)

try:
    secret_key = settings.SECRET_KEY
    if secret_key and len(secret_key) > 20:
        print(f"{GREEN}✓ SECRET_KEY is set and appears valid{RESET}")
        print(f"  Length: {len(secret_key)} characters")
        print(f"  Starts with: {secret_key[:10]}...")
        
        # Test that sessions work
        session_count = Session.objects.count()
        print(f"  Current sessions: {session_count}")
        test_results['passed'].append('Django SECRET_KEY')
    else:
        print(f"{RED}✗ SECRET_KEY appears invalid{RESET}")
        test_results['failed'].append('Django SECRET_KEY')
except Exception as e:
    print(f"{RED}✗ Error checking SECRET_KEY: {str(e)}{RESET}")
    test_results['failed'].append('Django SECRET_KEY')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Field Encryption Key
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}TEST 2: Field Encryption Key (PII Protection){RESET}")
print("-" * 80)

try:
    encryption_key = settings.FIELD_ENCRYPTION_KEY
    if encryption_key:
        print(f"{GREEN}✓ FIELD_ENCRYPTION_KEY is set{RESET}")
        print(f"  Key length: {len(encryption_key)} characters")
        
        # Try to create a Fernet cipher to test key validity
        try:
            cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            test_message = b"test"
            encrypted = cipher.encrypt(test_message)
            decrypted = cipher.decrypt(encrypted)
            
            if decrypted == test_message:
                print(f"{GREEN}✓ Encryption/Decryption working correctly{RESET}")
                test_results['passed'].append('Field Encryption Key')
            else:
                print(f"{RED}✗ Encryption/Decryption failed{RESET}")
                test_results['failed'].append('Field Encryption Key')
        except Exception as e:
            print(f"{RED}✗ Cipher test failed: {str(e)}{RESET}")
            test_results['failed'].append('Field Encryption Key')
    else:
        print(f"{RED}✗ FIELD_ENCRYPTION_KEY not set{RESET}")
        test_results['failed'].append('Field Encryption Key')
except Exception as e:
    print(f"{RED}✗ Error checking FIELD_ENCRYPTION_KEY: {str(e)}{RESET}")
    test_results['failed'].append('Field Encryption Key')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: BulkSMS Credentials
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}TEST 3: BulkSMS Credentials{RESET}")
print("-" * 80)

try:
    bulksms_username = settings.BULKSMS_USERNAME
    bulksms_password = settings.BULKSMS_PASSWORD
    
    if bulksms_username and 'YOUR' not in bulksms_username:
        print(f"{GREEN}✓ BulkSMS credentials appear to be set{RESET}")
        print(f"  Username: {bulksms_username[:3]}...{bulksms_username[-3:]}")
        
        # Test API connection
        try:
            headers = {"Accept": "application/json"}
            auth = (bulksms_username, bulksms_password)
            response = requests.get(
                'https://api.bulksms.com/v1/contacts',
                headers=headers,
                auth=auth,
                timeout=5
            )
            print(f"  API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"{GREEN}✓ BulkSMS API authentication successful{RESET}")
                test_results['passed'].append('BulkSMS Credentials')
            elif response.status_code == 401:
                print(f"{RED}✗ BulkSMS API authentication failed (invalid credentials){RESET}")
                test_results['failed'].append('BulkSMS Credentials')
            else:
                print(f"{YELLOW}⚠ BulkSMS API returned status {response.status_code}{RESET}")
                test_results['warnings'].append('BulkSMS Credentials - unusual response')
        except requests.exceptions.Timeout:
            print(f"{YELLOW}⚠ BulkSMS API timeout (may be network issue){RESET}")
            test_results['warnings'].append('BulkSMS Credentials - timeout')
        except Exception as e:
            print(f"{YELLOW}⚠ Could not test BulkSMS API: {str(e)}{RESET}")
            test_results['warnings'].append(f'BulkSMS Credentials - {str(e)}')
    else:
        print(f"{YELLOW}⚠ BulkSMS credentials are placeholders{RESET}")
        test_results['warnings'].append('BulkSMS Credentials - not configured')
except Exception as e:
    print(f"{RED}✗ Error checking BulkSMS: {str(e)}{RESET}")
    test_results['failed'].append('BulkSMS Credentials')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: OpenAI API Key
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}TEST 4: OpenAI API Key{RESET}")
print("-" * 80)

try:
    openai_key = settings.OPENAI_API_KEY
    
    if openai_key and 'YOUR' not in openai_key and openai_key.startswith('sk-'):
        print(f"{GREEN}✓ OpenAI API key appears to be set{RESET}")
        print(f"  Key format: {openai_key[:7]}...{openai_key[-4:]}")
        
        # Test API connection
        try:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                'https://api.openai.com/v1/models',
                headers=headers,
                timeout=5
            )
            print(f"  API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"{GREEN}✓ OpenAI API authentication successful{RESET}")
                test_results['passed'].append('OpenAI API Key')
            elif response.status_code == 401:
                print(f"{RED}✗ OpenAI API authentication failed (invalid key){RESET}")
                test_results['failed'].append('OpenAI API Key')
            else:
                print(f"{YELLOW}⚠ OpenAI API returned status {response.status_code}{RESET}")
                test_results['warnings'].append('OpenAI API Key - unusual response')
        except requests.exceptions.Timeout:
            print(f"{YELLOW}⚠ OpenAI API timeout (may be network issue){RESET}")
            test_results['warnings'].append('OpenAI API Key - timeout')
        except Exception as e:
            print(f"{YELLOW}⚠ Could not test OpenAI API: {str(e)}{RESET}")
            test_results['warnings'].append(f'OpenAI API Key - {str(e)}')
    else:
        print(f"{YELLOW}⚠ OpenAI API key is not configured with valid format{RESET}")
        test_results['warnings'].append('OpenAI API Key - not configured')
except Exception as e:
    print(f"{RED}✗ Error checking OpenAI API Key: {str(e)}{RESET}")
    test_results['failed'].append('OpenAI API Key')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: Easypay Configuration
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}TEST 5: Easypay Configuration{RESET}")
print("-" * 80)

try:
    easypay_key = settings.EASYPAY_API_KEY
    easypay_url = settings.EASYPAY_URL
    easypay_receiver = settings.EASY_PAY_RECEIVER_ID
    
    print(f"  URL: {easypay_url}")
    print(f"  Receiver ID: {easypay_receiver}")
    
    if easypay_key and 'YOUR' not in easypay_key:
        print(f"{GREEN}✓ Easypay API key is set{RESET}")
        test_results['passed'].append('Easypay Configuration')
    else:
        print(f"{YELLOW}⚠ Easypay API key is placeholder (scheme-specific, expected){RESET}")
        test_results['warnings'].append('Easypay Configuration - per-scheme pending')
except Exception as e:
    print(f"{RED}✗ Error checking Easypay: {str(e)}{RESET}")
    test_results['failed'].append('Easypay Configuration')


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*80)
print("TEST RESULTS SUMMARY")
print("="*80)

print(f"\n{GREEN}✓ PASSED ({len(test_results['passed'])}):{RESET}")
for test in test_results['passed']:
    print(f"  ✓ {test}")

if test_results['failed']:
    print(f"\n{RED}✗ FAILED ({len(test_results['failed'])}):{RESET}")
    for test in test_results['failed']:
        print(f"  ✗ {test}")

if test_results['warnings']:
    print(f"\n{YELLOW}⚠ WARNINGS ({len(test_results['warnings'])}):{RESET}")
    for test in test_results['warnings']:
        print(f"  ⚠ {test}")

print("\n" + "="*80)

# Exit code
if test_results['failed']:
    print(f"\n{RED}PHASE 8 STATUS: NEEDS ATTENTION - {len(test_results['failed'])} test(s) failed{RESET}")
    sys.exit(1)
elif test_results['warnings']:
    print(f"\n{YELLOW}PHASE 8 STATUS: PARTIAL - {len(test_results['warnings'])} warning(s), ready for configuration{RESET}")
    sys.exit(0)
else:
    print(f"\n{GREEN}PHASE 8 STATUS: READY - All credentials configured and tested{RESET}")
    sys.exit(0)
