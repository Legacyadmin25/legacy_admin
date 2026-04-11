"""
Utilities for managing public applications and converting to policies
"""

from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

from members.models import Member, Policy, Dependent, Beneficiary
from members.models_public_enrollment import PublicApplication
from branches.models import Bank
from payments.models import Payment

logger = logging.getLogger(__name__)


def convert_application_to_policy(application, reviewed_by=None):
    """
    Convert approved PublicApplication to actual Policy
    Creates Member record if doesn't exist, then creates Policy
    
    Args:
        application: PublicApplication instance
        reviewed_by: User approving the conversion
    
    Returns:
        (success, policy_or_error_msg)
    """
    
    if application.status != 'approved':
        return False, "Application must be approved before conversion"
    
    if application.converted_policy:
        return False, "Application already converted to policy"
    
    try:
        with transaction.atomic():
            # Get or create member
            member, created = Member.objects.get_or_create(
                email=application.email,
                defaults={
                    'first_name': application.first_name,
                    'last_name': application.last_name,
                    'id_number': application.id_number or '',
                    'passport_number': application.passport_number or '',  # Ensure not NULL
                    'gender': application.gender,
                    'date_of_birth': application.date_of_birth,
                    'phone_number': application.phone_number,
                    'marital_status': application.marital_status,
                    'physical_address_line_1': application.physical_address_line_1,
                    'physical_address_line_2': application.physical_address_line_2,
                    'physical_address_city': application.physical_address_city,
                    'physical_address_postal_code': application.physical_address_postal_code,
                }
            )
            
            # Create policy
            policy = Policy.objects.create(
                member=member,
                scheme=application.scheme,
                plan=application.plan,
                payment_method=application.payment_method,
                underwritten_by=application.enrollment_link.agent if application.enrollment_link and application.enrollment_link.agent else None,
                is_complete=True,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            
            # Add payment details if debit order
            if application.payment_method == 'DEBIT_ORDER' and application.bank:
                policy.bank = application.bank
                policy.branch_code = application.branch_code
                policy.account_holder_name = application.account_holder_name
                policy.account_number = application.account_number
                policy.debit_instruction_day = application.debit_instruction_day
                policy.save()
            
            # Add cover amount from plan
            if application.plan:
                policy.cover_amount = application.plan.main_cover
                policy.premium_amount = application.plan.premium
                policy.save()

            # Create beneficiaries captured during public enrollment.
            answer_map = {
                a.question_key: (a.answer or '').strip()
                for a in application.answers.all()
            }

            for idx in (1, 2):
                first_name = answer_map.get(f'beneficiary_{idx}_first_name', '')
                last_name = answer_map.get(f'beneficiary_{idx}_last_name', '')
                relationship = answer_map.get(f'beneficiary_{idx}_relationship', '')
                share_raw = answer_map.get(f'beneficiary_{idx}_share', '')
                id_number = answer_map.get(f'beneficiary_{idx}_id_number', '')

                if not first_name or not last_name or not relationship:
                    continue

                try:
                    share = int(share_raw) if share_raw else (100 if idx == 1 else 0)
                except ValueError:
                    share = 100 if idx == 1 else 0

                if share <= 0:
                    continue

                Beneficiary.objects.create(
                    policy=policy,
                    first_name=first_name,
                    last_name=last_name,
                    relationship_to_main_member=relationship,
                    id_number=id_number,
                    share=share,
                )
            
            # Link application to policy
            application.converted_member = member
            application.converted_policy = policy
            application.completed_at = timezone.now()
            application.status = 'completed'
            application.reviewed_by = reviewed_by
            application.save()
            
            # Send policy document (PDF) to applicant
            try:
                from members.policy_documents import send_policy_document_email
                send_policy_document_email(application)
            except Exception as e:
                logger.error(f"Failed to send policy document email: {str(e)}")
            
            # Send confirmation to applicant
            send_policy_confirmation_email(application, policy, member)
            
            logger.info(
                f"Successfully converted application {application.application_id} "
                f"to policy {policy.id} for {member.first_name} {member.last_name}"
            )
            
            return True, policy
    
    except Exception as e:
        logger.error(f"Error converting application {application.id} to policy: {str(e)}")
        return False, str(e)


def send_policy_confirmation_email(application, policy, member):
    """Send confirmation email to member with policy details"""
    
    try:
        context = {
            'member_name': f"{member.first_name} {member.last_name}",
            'policy_number': policy.policy_number,
            'scheme_name': application.scheme.name,
            'plan_name': application.plan.name,
            'premium': application.plan.premium,
            'payment_method': application.get_payment_method_display(),
        }
        
        subject = f"Legacy Admin - Policy Approved: {policy.policy_number}"
        
        html_message = render_to_string(
            'members/public_enrollment/email_policy_confirmation.html',
            context
        )
        
        send_mail(
            subject,
            f"Your policy {policy.policy_number} has been created.",
            'noreply@legacyadmin.com',
            [application.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Confirmation email sent to {application.email}")
    
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {str(e)}")


def get_application_summary(application):
    """Get formatted summary of application data for review"""
    
    summary = {
        'application_id': application.application_id,
        'applicant_name': f"{application.first_name} {application.last_name}",
        'applicant_email': application.email,
        'applicant_phone': application.phone_number,
        'identification': f"{application.id_number or application.passport_number}",
        'date_of_birth': application.date_of_birth,
        'gender': application.gender,
        'marital_status': application.marital_status,
        'address': f"{application.physical_address_line_1}, {application.physical_address_city}",
        'scheme': application.scheme.name,
        'plan': application.plan.name,
        'premium': f"R{application.plan.premium:.2f}",
        'payment_method': application.get_payment_method_display(),
        'status': application.get_status_display(),
        'created_at': application.created_at,
        'submitted_at': application.submitted_at,
    }
    
    # Add conditional answers
    answers = {}
    for answer in application.answers.all():
        answers[answer.question_key] = answer.answer
    summary['answers'] = answers
    
    # Add POPIA consents
    consents = {}
    for consent in application.popia_consents.all():
        consents[consent.consent_type] = consent.consented
    summary['popia_consents'] = consents
    
    return summary


def reject_application(application, reason, reviewed_by=None):
    """
    Reject an application with reason
    Sends rejection email to applicant
    """
    
    try:
        application.status = 'rejected'
        application.review_notes = reason
        application.reviewed_by = reviewed_by
        application.save()
        
        # Send rejection email
        context = {
            'member_name': f"{application.first_name} {application.last_name}",
            'reason': reason,
            'app_ref': application.application_id,
        }
        
        subject = f"Legacy Admin - Application {application.application_id} - Update"
        
        html_message = render_to_string(
            'members/public_enrollment/email_application_rejected.html',
            context
        )
        
        send_mail(
            subject,
            f"Your application {application.application_id} has been reviewed.",
            'noreply@legacyadmin.com',
            [application.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Application {application.application_id} rejected: {reason}")
        return True
    
    except Exception as e:
        logger.error(f"Error rejecting application: {str(e)}")
        return False


def get_pending_applications_for_user(user):
    """
    Get pending applications visible to this user
    based on their scheme/branch/agent assignment
    """
    
    from django.db.models import Q
    from schemes.models import Scheme
    from settings_app.models import Agent
    
    # Superuser sees all
    if user.is_superuser:
        return PublicApplication.objects.filter(status='submitted')
    
    # Get user's schemes
    user_schemes = []
    
    # If user is scheme manager
    if user.groups.filter(name='Scheme Manager').exists():
        # Get scheme from user profile or assignment
        # This depends on your user assignment logic
        pass
    
    # If user is branch owner/manager
    if user.groups.filter(name='Branch Manager').exists():
        # Get assigned branches
        pass
    
    # Get all submitted applications for visible schemes/branches
    applications = PublicApplication.objects.filter(status='submitted')
    
    return applications.order_by('-submitted_at')


def generate_enrollment_link_qrcode(link):
    """
    Generate QR code for enrollment link
    Returns base64 encoded PNG image
    """
    
    try:
        import qrcode
        import io
        import base64
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        
        # Use full URL
        url = f"https://yoursite.com/apply/{link.token}/"
        qr.add_data(url)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return None


def get_enrollment_statistics(scheme=None):
    """
    Get enrollment statistics for dashboard
    """
    
    query = PublicApplication.objects.all()
    
    if scheme:
        query = query.filter(scheme=scheme)
    
    return {
        'total': query.count(),
        'draft': query.filter(status='draft').count(),
        'submitted': query.filter(status='submitted').count(),
        'approved': query.filter(status='approved').count(),
        'rejected': query.filter(status='rejected').count(),
        'completed': query.filter(status='completed').count(),
    }
