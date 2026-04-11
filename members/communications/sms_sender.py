import logging
import base64
import os
import re
import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
from members.communications.models import SMSLog  # direct import

logger = logging.getLogger(__name__)

# Settings
BULKSMS_API_URL = 'https://api.bulksms.com/v1'


def normalize_phone_number(phone_number: str) -> str:
    """Normalize SA mobile numbers to +27 format for SMS delivery."""
    if not phone_number:
        return phone_number

    normalized = re.sub(r'\s+', '', str(phone_number))
    if normalized.startswith('+27'):
        return normalized
    if normalized.startswith('27'):
        return f'+{normalized}'
    if normalized.startswith('0'):
        return f'+27{normalized[1:]}'
    return normalized


def get_bulksms_auth():
    """
    Get BulkSMS authentication method.
    
    Supports two methods:
    1. API Token (recommended for MFA-enabled accounts)
       Format: TOKEN_ID:TOKEN_SECRET
    2. Basic Auth (username/password)
    """
    # Check for API token first (recommended)
    api_token = os.getenv('BULKSMS_API_TOKEN')
    if api_token:
        # BulkSMS API token format: use as Bearer token or Basic auth
        # The token ID:secret can be used as Basic auth credentials
        try:
            # Try to use it as Bearer token directly
            return {
                'auth_type': 'bearer',
                'token': api_token,
                'headers': {
                    'Authorization': f'Bearer {api_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }
        except:
            pass
    
    # Fall back to basic auth with token credentials
    username = os.getenv('BULKSMS_USERNAME')
    password = os.getenv('BULKSMS_PASSWORD')
    
    if username and password:
        # Use token ID and secret as basic auth
        return {
            'auth_type': 'basic',
            'auth': HTTPBasicAuth(username, password),
            'headers': {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        }
    
    return None


def send_bulksms(to: str, message: str, test_mode: bool = False) -> SMSLog:
    """
    Sends an SMS via BulkSMS API (JSON v1).
    
    Args:
        to: Phone number (e.g., "+27712345678")
        message: SMS message text
        test_mode: If True, logs to console instead of sending (development)
    
    Returns:
        SMSLog instance with status
    """
    
    to = normalize_phone_number(to)

    # Test mode: print to console instead of sending
    if test_mode or os.getenv('OTP_TEST_MODE') == 'True':
        logger.info(f"[TEST MODE] SMS to {to}: {message}")
        sms_log = SMSLog.objects.create(
            phone_number=to,
            message=message,
            status="TEST",
            detail=f"Test mode - message would be sent to {to}"
        )
        return sms_log
    
    # Get authentication
    auth_config = get_bulksms_auth()
    if not auth_config:
        logger.error("BulkSMS credentials not configured")
        sms_log = SMSLog.objects.create(
            phone_number=to,
            message=message,
            status="FAILED",
            detail="BulkSMS credentials not configured"
        )
        return sms_log
    
    # Prepare request
    url = f"{BULKSMS_API_URL}/messages"
    payload = {
        "to": to,
        "body": message,
        "encoding": "UTF-8"
    }
    
    headers = auth_config.get('headers', {})
    headers['Accept'] = 'application/json'
    headers['Content-Type'] = 'application/json'
    
    try:
        # Send SMS
        if auth_config['auth_type'] == 'bearer':
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )
        else:  # basic auth
            response = requests.post(
                url,
                json=payload,
                auth=auth_config['auth'],
                headers=headers,
                timeout=10
            )
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        status = "SENT"
        detail = result.get('body', 'Message queued for delivery')
        
        logger.info(f"SMS sent to {to}: {detail}")
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            logger.error(f"BulkSMS authentication failed: {e}")
            status = "FAILED"
            detail = "Authentication failed - check credentials"
        else:
            logger.error(f"BulkSMS HTTP error {response.status_code}: {e}")
            status = "FAILED"
            detail = f"HTTP {response.status_code}: {response.text}"
    
    except requests.exceptions.Timeout:
        logger.error(f"BulkSMS timeout sending to {to}")
        status = "FAILED"
        detail = "Request timeout"
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"BulkSMS connection error: {e}")
        status = "FAILED"
        detail = f"Network error: {str(e)}"
    
    except Exception as e:
        logger.exception(f"Unexpected error sending SMS to {to}")
        status = "FAILED"
        detail = str(e)
    
    # Create SMS log record
    sms_log = SMSLog.objects.create(
        phone_number=to,
        message=message,
        status=status,
        detail=detail
    )
    return sms_log


def send_bulk_sms(to: str, message: str) -> SMSLog:
    """
    Legacy function name - delegates to send_bulksms()
    Kept for backward compatibility
    """
    return send_bulksms(to, message)


def send_otp_sms(to: str, otp_code: str) -> SMSLog:
    """
    Send OTP verification SMS.
    
    Args:
        to: Phone number
        otp_code: 6-digit OTP code
    
    Returns:
        SMSLog instance
    """
    message = f"Your verification code is: {otp_code}. Valid for 15 minutes. Do not share this code."
    return send_bulksms(to, message)


# Backward compatibility - allow old import path
send_sms = send_bulksms

