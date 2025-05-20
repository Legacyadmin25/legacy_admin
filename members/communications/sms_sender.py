import logging
import requests
from django.conf import settings
from members.communications.models import SMSLog  # direct import

logger = logging.getLogger(__name__)


def send_bulk_sms(to: str, message: str) -> SMSLog:
    """
    Sends an SMS via BulkSMS JSON API and logs the result.
    Returns the created SMSLog instance.
    """
    payload = {
        "api_key": settings.SMS_API_KEY,
        "api_secret": settings.SMS_API_SECRET,
        "to": to,
        "message": message,
    }

    try:
        response = requests.post(
            "https://api.bulksmsprovider.com/send",  # adjust to your actual endpoint
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        status = "SENT"
        detail = response.json().get("message", "")
    except Exception as e:
        status = "FAILED"
        detail = str(e)
        logger.exception(f"Failed to send SMS to {to}")

    # Create and return an SMSLog record
    sms_log = SMSLog.objects.create(
        phone_number=to,
        message=message,
        status=status,
        detail=detail
    )
    return sms_log
