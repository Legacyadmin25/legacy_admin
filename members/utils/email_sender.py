# members/utils/email_sender.py

import logging
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_policy_document_email(policy):
    """
    Send the policy document as an email attachment to the member.
    
    Args:
        policy: The Policy model instance
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    member = policy.member
    
    # Check if we have all required data
    if not member.email:
        logger.warning(f"Cannot send policy document email: No email address for member {member.id}")
        return False
        
    if not policy.document:
        logger.warning(f"Cannot send policy document email: No document for policy {policy.id}")
        return False
    
    # Check if email was already sent
    if policy.email_sent_at:
        logger.info(f"Policy document email already sent to {member.email} at {policy.email_sent_at}")
        return True
    
    try:
        # Prepare email
        subject = "Your Legacy Guard Policy Document"
        body = f"""Dear {member.get_full_name()},

Attached is your official Legacy Guard policy document.

Thank you for choosing Legacy Guard for your funeral cover.

Best regards,
Legacy Guard Support Team
"""
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'policies@legacyguard.co.za')
        
        # Create email message
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[member.email],
        )
        
        # Attach the policy document
        document_name = f"LegacyPolicy_{policy.policy_number}.pdf"
        email.attach(document_name, policy.document.read(), 'application/pdf')
        
        # Send the email
        email.send(fail_silently=False)
        
        # Update the policy to record that the email was sent
        policy.email_sent_at = timezone.now()
        policy.save(update_fields=['email_sent_at'])
        
        logger.info(f"Policy document email sent successfully to {member.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send policy document email to {member.email}: {str(e)}")
        return False
