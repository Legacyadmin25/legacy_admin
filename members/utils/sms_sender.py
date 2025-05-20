# members/utils/sms_sender.py

import requests
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms(phone_number, message):
    """
    Send an SMS using the BulkSMS API.
    
    Args:
        phone_number (str): The recipient's phone number in international format (e.g., +27123456789)
        message (str): The message content to send
        
    Returns:
        dict: The API response or error information
    """
    # Get API credentials from settings
    api_token = getattr(settings, 'BULKSMS_API_TOKEN', '')
    api_id = getattr(settings, 'BULKSMS_API_ID', '')
    
    if not api_token or not api_id:
        logger.error("BulkSMS API credentials not configured")
        return {
            'success': False,
            'error': 'API credentials not configured'
        }
    
    # Format phone number (ensure it has international prefix)
    if not phone_number.startswith('+'):
        # Default to South Africa if no prefix
        phone_number = '+27' + phone_number.lstrip('0')
    
    # Create Basic Auth header
    auth_string = f"{api_id}:{api_token}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    
    # Prepare request
    url = "https://api.bulksms.com/v1/messages"
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": [phone_number],
        "body": message
    }
    
    try:
        # Send the request
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        return {
            'success': True,
            'response': response.json()
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"SMS sending failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def send_otp(phone_number, otp_code):
    """
    Send an OTP code via SMS.
    
    Args:
        phone_number (str): The recipient's phone number
        otp_code (str): The OTP code to send
        
    Returns:
        dict: The result of the SMS sending operation
    """
    message = f"Your Legacy policy OTP is {otp_code}. Valid for 10 minutes."
    return send_sms(phone_number, message)

def send_policy_confirmation(phone_number, policy_number):
    """
    Send a policy confirmation SMS.
    
    Args:
        phone_number (str): The recipient's phone number
        policy_number (str): The policy number to include in the message
        
    Returns:
        dict: The result of the SMS sending operation
    """
    message = f"Your Legacy policy has been confirmed. Policy #: {policy_number}"
    return send_sms(phone_number, message)
