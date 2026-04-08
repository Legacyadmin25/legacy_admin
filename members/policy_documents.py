"""
Policy Document Generation for Public Enrollment
Generates PDF policy documents and sends via email to clients
"""

import io
import importlib
import logging
from datetime import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_pisa():
    try:
        module = importlib.import_module('xhtml2pdf')
    except ImportError as exc:
        raise RuntimeError('xhtml2pdf is required to generate policy PDFs') from exc
    return module.pisa


def generate_policy_pdf(application):
    """
    Generate PDF policy document from HTML template
    
    Args:
        application: PublicApplication instance
        
    Returns:
        bytes: PDF file content
    """
    try:
        pisa = _get_pisa()

        # Prepare context data
        context = {
            'application': application,
            'policy': application.converted_policy if application.converted_policy else None,
            'generated_date': datetime.now(),
            'company_name': getattr(settings, 'COMPANY_NAME', 'LegacyGuard'),
            'company_logo': getattr(settings, 'COMPANY_LOGO_URL', ''),
        }
        
        # Render HTML template
        html_string = render_to_string('members/public_enrollment/policy_document.html', context)
        
        # Convert HTML to PDF
        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(
            html_string,
            dest=pdf_buffer,
            encoding='UTF-8',
            pagesize='A4'
        )
        
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating policy PDF: {str(e)}")
        raise


def send_policy_document_email(application):
    """
    Generate policy PDF and send via email to applicant
    
    Args:
        application: PublicApplication instance
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Generate PDF
        pdf_content = generate_policy_pdf(application)
        
        # Prepare email
        subject = f"Your Policy Document - Reference {application.id}"
        
        email_context = {
            'first_name': application.first_name,
            'reference_number': application.id,
            'policy_number': application.converted_policy.policy_number if application.converted_policy else 'Pending',
            'plan_name': application.plan.name,
            'premium': application.plan.premium,
            'company_name': getattr(settings, 'COMPANY_NAME', 'LegacyGuard'),
        }
        
        # Render email body
        email_html = render_to_string('members/public_enrollment/policy_email.html', email_context)
        email_text = f"""
Dear {application.first_name},

Your policy application has been approved! Your policy document is attached.

Reference Number: {application.id}
Policy: {application.plan.name}
Monthly Premium: R{application.plan.premium}

Please keep this document for your records. If you have any questions, contact our support team.

Best regards,
{getattr(settings, 'COMPANY_NAME', 'LegacyGuard')}
"""
        
        # Send email with PDF attachment
        email = EmailMessage(
            subject=subject,
            body=email_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email],
            html_message=email_html,
        )
        
        # Attach PDF
        email.attach(
            filename=f"Policy_{application.id}.pdf",
            content=pdf_content,
            mimetype='application/pdf'
        )
        
        # Send
        email.send()
        logger.info(f"Policy document email sent to {application.email} for application {application.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending policy document email: {str(e)}")
        return False


def send_approval_notification(application):
    """
    Send email notification when application is approved
    
    Args:
        application: PublicApplication instance
    """
    try:
        subject = f"Application Approved - Reference {application.id}"
        
        email_context = {
            'first_name': application.first_name,
            'reference_number': application.id,
            'plan_name': application.plan.name,
            'company_name': getattr(settings, 'COMPANY_NAME', 'LegacyGuard'),
        }
        
        email_html = render_to_string('members/public_enrollment/approval_notification.html', email_context)
        
        email_text = f"""
Dear {application.first_name},

Great news! Your policy application has been approved.

Your policy document has been attached and sent separately with all the details.

Reference Number: {application.id}
Status: APPROVED

If you have any questions, please contact us.

Best regards,
{getattr(settings, 'COMPANY_NAME', 'LegacyGuard')}
"""
        
        email = EmailMessage(
            subject=subject,
            body=email_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email],
            html_message=email_html,
        )
        
        email.send()
        logger.info(f"Approval notification sent to {application.email}")
        
    except Exception as e:
        logger.error(f"Error sending approval notification: {str(e)}")
