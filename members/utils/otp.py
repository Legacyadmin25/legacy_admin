# members/utils/otp.py

import random
import string
import hashlib
import datetime
from django.utils import timezone

def generate_otp(length=6):
    """
    Generate a random numeric OTP of specified length.
    
    Args:
        length (int): Length of the OTP code (default: 6)
        
    Returns:
        str: The generated OTP code
    """
    # Generate a random numeric string of specified length
    return ''.join(random.choices(string.digits, k=length))

def hash_otp(otp_code):
    """
    Create a secure hash of an OTP code.
    
    Args:
        otp_code (str): The OTP code to hash
        
    Returns:
        str: The hashed OTP code
    """
    # Create a SHA-256 hash of the OTP code
    return hashlib.sha256(otp_code.encode()).hexdigest()

def verify_otp(entered_otp, stored_hash, sent_at, expiry_minutes=10):
    """
    Verify an entered OTP against a stored hash and check if it's still valid.
    
    Args:
        entered_otp (str): The OTP entered by the user
        stored_hash (str): The stored hash of the original OTP
        sent_at (datetime): When the OTP was sent
        expiry_minutes (int): How many minutes the OTP is valid for
        
    Returns:
        bool: True if the OTP is valid and not expired, False otherwise
    """
    # Check if the OTP has expired
    now = timezone.now()
    expiry_time = sent_at + datetime.timedelta(minutes=expiry_minutes)
    
    if now > expiry_time:
        return False
    
    # Hash the entered OTP and compare with the stored hash
    entered_hash = hash_otp(entered_otp)
    return entered_hash == stored_hash
