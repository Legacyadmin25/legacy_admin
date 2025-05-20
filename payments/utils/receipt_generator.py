import os
import logging
from io import BytesIO
from datetime import datetime
from django.template.loader import get_template
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from weasyprint import HTML, CSS

from payments.models import Payment, PaymentReceipt

logger = logging.getLogger(__name__)

def generate_payment_receipt_pdf(payment):
    """
    Generate a PDF receipt for a payment.
    
    Args:
        payment: The Payment model instance
        
    Returns:
        ContentFile: A Django ContentFile containing the PDF
    """
    # Get related data
    member = payment.member
    policy = payment.policy
    
    # Prepare context for template
    context = {
        'payment': payment,
        'member': member,
        'policy': policy,
        'generated_at': timezone.now(),
        'company_name': getattr(settings, 'COMPANY_NAME', 'Legacy Guard'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', '123 Main Street, Pretoria'),
        'company_phone': getattr(settings, 'COMPANY_PHONE', '012 345 6789'),
        'company_email': getattr(settings, 'COMPANY_EMAIL', 'info@legacyguard.co.za'),
        'company_website': getattr(settings, 'COMPANY_WEBSITE', 'www.legacyguard.co.za'),
        'company_logo': getattr(settings, 'COMPANY_LOGO', '/static/img/logo.png'),
    }
    
    # Render HTML template
    template = get_template('payments/pdf/payment_receipt.html')
    html_string = template.render(context)
    
    # Create PDF
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(
        pdf_file,
        stylesheets=[
            CSS(string='@page { size: A4; margin: 1cm }')
        ]
    )
    
    # Reset file pointer
    pdf_file.seek(0)
    
    # Create a ContentFile
    filename = f"receipt_{payment.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    return ContentFile(pdf_file.read(), name=filename)

def create_payment_receipt(payment, user=None):
    """
    Create a payment receipt record and generate the PDF.
    
    Args:
        payment: The Payment model instance
        user: The User creating the receipt (optional)
        
    Returns:
        PaymentReceipt: The created receipt instance
    """
    try:
        # Generate receipt number
        receipt_number = f"R{payment.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Generate PDF
        pdf_content = generate_payment_receipt_pdf(payment)
        
        # Create receipt record
        receipt = PaymentReceipt.objects.create(
            payment=payment,
            receipt_number=receipt_number,
            status='GENERATED',
            sent_by=user
        )
        
        # Save PDF to receipt
        receipt.pdf_file.save(pdf_content.name, pdf_content)
        
        return receipt
        
    except Exception as e:
        logger.error(f"Error creating payment receipt: {str(e)}")
        return None

def send_receipt_email(receipt, email_address):
    """
    Send a payment receipt via email.
    
    Args:
        receipt: The PaymentReceipt instance
        email_address: Email address to send to
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        payment = receipt.payment
        member = payment.member
        
        # Prepare email
        subject = f"Payment Receipt - {receipt.receipt_number}"
        body = f"""Dear {member.first_name} {member.last_name},

Thank you for your payment of R{payment.amount} on {payment.date}.

Your receipt is attached to this email.

Best regards,
{getattr(settings, 'COMPANY_NAME', 'Legacy Guard')} Support Team
"""
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'receipts@legacyguard.co.za')
        
        # Create email message
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[email_address],
        )
        
        # Attach the receipt
        receipt_name = f"Receipt_{receipt.receipt_number}.pdf"
        email.attach(receipt_name, receipt.pdf_file.read(), 'application/pdf')
        
        # Send email
        email.send(fail_silently=False)
        
        # Update receipt status
        receipt.status = 'EMAILED'
        receipt.sent_to = email_address
        receipt.sent_at = timezone.now()
        receipt.save()
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending receipt email: {str(e)}")
        return False

def get_whatsapp_link(phone_number, receipt_number):
    """
    Generate a WhatsApp link for sending a message about the receipt.
    
    Args:
        phone_number: The phone number to send to
        receipt_number: The receipt number
        
    Returns:
        str: WhatsApp link
    """
    # Format phone number (remove spaces, add country code if needed)
    if phone_number.startswith('0'):
        phone_number = '+27' + phone_number[1:]
    
    # Remove any non-numeric characters
    phone_number = ''.join(c for c in phone_number if c.isdigit() or c == '+')
    
    # Create message
    message = f"Your payment receipt {receipt_number} is ready. Thank you for your payment."
    
    # Generate link
    return f"https://wa.me/{phone_number}?text={message}"
