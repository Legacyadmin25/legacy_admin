#!/usr/bin/env python
"""
Updated BulkSMS Test - Tests API Token Support
Tests both API Token and Basic Auth methods
Run: python test_bulksms_updated.py
"""

import os
import json
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_env_vars():
    """Check .env configuration"""
    print("\n" + "="*70)
    print("🔐 ENVIRONMENT CONFIGURATION CHECK")
    print("="*70)
    
    bulksms_user = os.getenv('BULKSMS_USERNAME')
    bulksms_pass = os.getenv('BULKSMS_PASSWORD')
    bulksms_token = os.getenv('BULKSMS_API_TOKEN')
    otp_test_mode = os.getenv('OTP_TEST_MODE')
    
    print(f"\n✓ Settings loaded from .env")
    print(f"  BULKSMS_USERNAME: {bulksms_user if bulksms_user else 'NOT SET'}")
    print(f"  BULKSMS_PASSWORD: {'***' + ('*'*max(0, len(bulksms_pass)-4)) if bulksms_pass else 'NOT SET'}")
    print(f"  BULKSMS_API_TOKEN: {('***' + bulksms_token[-10:]) if bulksms_token else 'NOT SET'}")
    print(f"  OTP_TEST_MODE: {otp_test_mode or 'False'}")
    
    if not bulksms_user and not bulksms_token:
        print("\n⚠️  WARNING: Neither API token nor username is set!")
        print("   You need at least one of:")
        print("   - BULKSMS_API_TOKEN (recommended)")
        print("   - BULKSMS_USERNAME + BULKSMS_PASSWORD")
        return False
    
    return True


def test_sms_sender_import():
    """Test if SMS sender module imports correctly"""
    print("\n" + "="*70)
    print("📦 SMS SENDER MODULE TEST")
    print("="*70)
    
    try:
        # Configure Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacyadmin.settings')
        
        import django
        django.setup()
        
        # Now import SMS sender
        from members.communications.sms_sender import (
            send_otp_sms, send_bulksms, get_bulksms_auth
        )
        
        print("\n✅ SMS sender module imported successfully")
        
        # Test auth detection
        auth_config = get_bulksms_auth()
        if auth_config:
            print(f"✅ BulkSMS auth configured: {auth_config.get('auth_type')}")
            if auth_config.get('auth_type') == 'bearer':
                print("   Using API Token (Recommended)")
            else:
                print("   Using Basic Auth (Username/Password)")
        else:
            print("⚠️  No BulkSMS credentials configured")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import SMS sender: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_otp_message_simulation():
    """Simulate OTP message that would be sent"""
    print("\n" + "="*70)
    print("📱 OTP MESSAGE SIMULATION")
    print("="*70)
    
    # Simulate OTP
    otp_code = "123456"
    phone = "+27722123456"
    
    message = f"Your verification code is: {otp_code}. Valid for 15 minutes. Do not share this code."
    
    print(f"\nPhone: {phone}")
    print(f"OTP Code: {otp_code}")
    print(f"Message ({len(message)} chars):\n  \"{message}\"")
    
    if len(message) <= 160:
        print(f"\n✅ Message fits in single SMS")
    else:
        parts = (len(message) + 159) // 160
        print(f"\n⚠️  Message requires {parts} SMS parts")
    
    return True


def test_authentication_flow():
    """Demonstrate the authentication flow"""
    print("\n" + "="*70)
    print("🔑 AUTHENTICATION FLOW")
    print("="*70)
    
    token = os.getenv('BULKSMS_API_TOKEN')
    username = os.getenv('BULKSMS_USERNAME')
    password = os.getenv('BULKSMS_PASSWORD')
    
    print("\n📋 Priority Order:")
    
    if token:
        print("\n1️⃣  ✅ API TOKEN FOUND (Using this)")
        print(f"    Token: {token[:20]}...{token[-10:]}")
        print("\n    Request Header:")
        print(f"    Authorization: Bearer {token[:20]}...{token[-10:]}")
        auth_method = "Bearer Token (API Token)"
    elif username and password:
        print(f"\n2️⃣  ✅ BASIC AUTH CREDENTIALS FOUND (Using this)")
        print(f"    Username: {username}")
        print(f"    Password: {'*' * len(password)}")
        print("\n    Request Header:")
        print(f"    Authorization: Basic [base64-encoded-credentials]")
        auth_method = "Basic Auth (Username/Password)"
    else:
        print("\n3️⃣  ❌ NO CREDENTIALS FOUND")
        print("\n    Solution:")
        print("    Add one of these to .env:")
        print("    - BULKSMS_API_TOKEN=your_token_here")
        print("    - BULKSMS_USERNAME=your_username")
        print("      BULKSMS_PASSWORD=your_password")
        auth_method = None
    
    if auth_method:
        print(f"\n✅ Auth Method: {auth_method}")
        return True
    
    return False


def test_mfa_recommendation():
    """Show MFA recommendations"""
    print("\n" + "="*70)
    print("⚠️  MFA ACCOUNT DETECTED")
    print("="*70)
    
    print("\n" + "Since your account has MFA enabled:")
    print("\n✅ RECOMMENDED: Use API Token")
    print("   1. Login to BulkSMS dashboard")
    print("   2. Go to: Settings > API > Tokens")
    print("   3. Create new token")
    print("   4. Add to .env: BULKSMS_API_TOKEN=<token>")
    
    print("\n⚠️  ALTERNATIVE: Create App Password")
    print("   1. Login to BulkSMS dashboard")
    print("   2. Go to: Security > App Passwords")
    print("   3. Generate password for 'API Access'")
    print("   4. Use as BULKSMS_PASSWORD")
    
    print("\n❌ NOT RECOMMENDED: Disable MFA")
    print("   (Security risk - not advisable)")


def main():
    """Run all tests"""
    print("\n" + "█"*70)
    print("█  BULKSMS SMS SENDER - UPDATED TEST SUITE")
    print("█  Supports API Token, Basic Auth, and MFA")
    print("█"*70)
    
    tests = [
        ("Environment Check", test_env_vars),
        ("SMS Sender Import", test_sms_sender_import),
        ("OTP Message Sim", test_otp_message_simulation),
        ("Auth Flow", test_authentication_flow),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ ERROR in {name}: {e}")
            results[name] = False
    
    # Show MFA info
    test_mfa_recommendation()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    # Next steps
    print("\n" + "="*70)
    print("📋 NEXT STEPS")
    print("="*70)
    
    token = os.getenv('BULKSMS_API_TOKEN')
    username = os.getenv('BULKSMS_USERNAME')
    
    if token:
        print("\n✅ API Token is configured")
        print("   Public enrollment OTP is ready to use!")
        print("\n   Run migrations:")
        print("   $ python manage.py makemigrations members")
        print("   $ python manage.py migrate members")
    elif username:
        print("\n⚠️  Using Basic Auth (username/password)")
        print("   Your account has MFA - this may fail!")
        print("\n   Recommended: Generate API token instead")
        print("   See setup instructions above")
    else:
        print("\n❌ No credentials configured")
        print("   Update .env and try again")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
