# members/utils/links.py

from django.conf import settings
from urllib.parse import urlencode

def payment_link(easypay_no, amount, method="generic"):
    """
    Produces a URL for Easypay payment.
    
    Args:
        easypay_no (str): The Easypay number
        amount (float): The payment amount
        method (str): The payment method (default: "generic")
    
    Returns:
        str: URL for Easypay payment
    """
    base_url = "https://www.easypay.co.za"
    
    # Format amount to 2 decimal places without decimal point
    # e.g., 100.50 becomes 10050
    formatted_amount = str(int(float(amount) * 100))
    
    # Build query parameters
    params = {
        'b': easypay_no,
        'a': formatted_amount
    }
    
    # Construct the full URL
    url = f"{base_url}/{method}?{urlencode(params)}"
    
    return url
