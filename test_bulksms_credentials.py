#!/usr/bin/env python
"""
BulkSMS Credential Verification Test
Tests the BulkSMS API integration with provided credentials
Run: python test_bulksms_credentials.py
"""

import os
import json
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# BulkSMS Configuration
BULKSMS_USERNAME = os.getenv('BULKSMS_USERNAME')
BULKSMS_PASSWORD = os.getenv('BULKSMS_PASSWORD')
BULKSMS_API_URL = 'https://api.bulksms.com/v1'

def test_bulksms_authentication():
    """Test BulkSMS API authentication"""
    print("\n" + "="*70)
    print("🔐 BULKSMS AUTHENTICATION TEST")
    print("="*70)
    
    if not BULKSMS_USERNAME or not BULKSMS_PASSWORD:
        print("❌ FAILED: BulkSMS credentials not found in .env")
        print(f"   BULKSMS_USERNAME: {BULKSMS_USERNAME}")
        print(f"   BULKSMS_PASSWORD: {'***' if BULKSMS_PASSWORD else 'NOT SET'}")
        return False
    
    print(f"✓ Credentials found:")
    print(f"  Username: {BULKSMS_USERNAME}")
    print(f"  Password: ***{'*' * max(0, len(BULKSMS_PASSWORD)-4)}")
    
    # Test API authentication
    print("\n🔍 Testing API connection...")
    
    try:
        # Use the account balance endpoint as a test
        url = f"{BULKSMS_API_URL}/account/balance"
        
        response = requests.get(
            url,
            auth=(BULKSMS_USERNAME, BULKSMS_PASSWORD),
            timeout=10,
            headers={'Accept': 'application/json'}
        )
        
        print(f"   Request URL: {url}")
        print(f"   HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ AUTHENTICATED SUCCESSFULLY")
            print(f"\n   Account Balance Details:")
            print(f"     - Credit: {data.get('credit', 'N/A')} units")
            print(f"     - Status: {data.get('status', 'N/A')}")
            return True
        
        elif response.status_code == 401:
            print("   ❌ AUTHENTICATION FAILED (401 Unauthorized)")
            print(f"   Response: {response.text}")
            return False
        
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: Connection to BulkSMS API timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False


def test_otp_message_format():
    """Test OTP message construction"""
    print("\n" + "="*70)
    print("📱 OTP MESSAGE FORMAT TEST")
    print("="*70)
    
    # Simulate OTP message
    otp_code = "123456"
    phone_number = "+27722123456"
    
    message = f"Your verification code is: {otp_code}. Valid for 15 minutes. Do not share this code."
    
    print(f"\nPhone Number: {phone_number}")
    print(f"OTP Code: {otp_code}")
    print(f"Message: {message}")
    print(f"Message Length: {len(message)} characters")
    
    if len(message) <= 160:
        print("✅ Message fits in single SMS (≤160 chars)")
    else:
        parts = (len(message) + 159) // 160
        print(f"⚠️  Message requires {parts} SMS parts")
    
    return True


def test_bulksms_send_simulation():
    """Simulate what the OTP sending will do"""
    print("\n" + "="*70)
    print("📤 SIMULATED OTP SEND")
    print("="*70)
    
    print("\nWhen user requests OTP in public enrollment:")
    print("\n1. Generate 6-digit code: 123456")
    print("2. Create PublicApplication record")
    print("3. Create OTPVerification record with:")
    print("   - otp_code: 123456")
    print("   - phone_number: (from user input)")
    print("   - expires_at: now + 15 minutes")
    print("   - status: 'pending'")
    print("\n4. Send SMS via BulkSMS API:")
    print("   POST /v1/messages")
    print("   Headers: Authorization: Basic (base64 encoded)")
    print("   Body: {")
    print("       'to': '+27722123456',")
    print("       'body': 'Your verification code is: 123456...',")
    print("       'encoding': 'UTF-8'")
    print("   }")
    print("\n5. Wait for response (usually < 1 second)")
    print("6. If successful: redirect to OTP verification page")
    print("7. If failed: show error, let user retry")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "█"*70)
    print("█  BULKSMS CREDENTIAL VERIFICATION SUITE")
    print("█  Testing integration with Public Enrollment OTP System")
    print("█"*70)
    
    results = {
        'Authentication': test_bulksms_authentication(),
        'Message Format': test_otp_message_format(),
        'Send Simulation': test_bulksms_send_simulation(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if results['Authentication']:
        print("\n✅ BulkSMS credentials are VALID and WORKING")
        print("   Public enrollment OTP system is ready to use!")
        print("\n   Next step: Run database migrations")
        print("   $ python manage.py makemigrations members")
        print("   $ python manage.py migrate members")
        return 0
    else:
        print("\n❌ BulkSMS credentials failed authentication")
        print("   Check username/password and try again")
        print("   Ensure account has SMS credit available")
        return 1


if __name__ == '__main__':
    exit(main())
