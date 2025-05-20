# members/utils/pdf_generator.py

import os
from io import BytesIO
from django.template.loader import get_template
from django.http import HttpResponse
from django.conf import settings
from weasyprint import HTML, CSS
from django.core.files.base import ContentFile
from django.db.models import Sum

def generate_policy_document(policy):
    """
    Generate a PDF policy document for a given policy.
    
    Args:
        policy: The Policy model instance
        
    Returns:
        ContentFile: A Django ContentFile containing the PDF
    """
    # Get related data
    member = policy.member
    
    # Get spouse if exists
    spouse = policy.dependent_set.filter(relationship_type='SPOUSE').first()
    
    # Get children
    children = policy.dependent_set.filter(relationship_type='CHILD')
    
    # Get extended family
    extended_family = policy.dependent_set.filter(
        relationship_type__in=['PARENT', 'PARENT_IN_LAW', 'EXTENDED']
    )
    
    # Get beneficiaries
    beneficiaries = policy.beneficiary_set.all()
    
    # Calculate totals
    # Main member cover and premium
    total_cover = policy.plan.cover_amount if policy.plan else 0
    total_premium = policy.plan.premium if policy.plan else 0
    
    # Add dependents cover and premium
    dependents_cover = policy.dependent_set.aggregate(total=Sum('cover_amount'))
    dependents_premium = policy.dependent_set.aggregate(total=Sum('premium'))
    
    if dependents_cover['total']:
        total_cover += dependents_cover['total']
    
    if dependents_premium['total']:
        total_premium += dependents_premium['total']
    
    # Prepare context for template
    context = {
        'policy': policy,
        'member': member,
        'spouse': spouse,
        'children': children,
        'extended_family': extended_family,
        'beneficiaries': beneficiaries,
        'total_cover': total_cover,
        'total_premium': total_premium,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    
    # Render template
    template = get_template('members/pdf/policy_document.html')
    html_string = template.render(context)
    
    # Generate PDF using WeasyPrint
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(
        pdf_file,
        stylesheets=[
            CSS(string='@page { size: A4; margin: 2cm; }')
        ]
    )
    
    # Create a ContentFile from the BytesIO buffer
    filename = f"LegacyPolicy_{policy.policy_number}.pdf"
    return ContentFile(pdf_file.getvalue(), name=filename)

def generate_and_save_policy_document(policy):
    """
    Generate a PDF policy document and save it to the policy model.
    
    Args:
        policy: The Policy model instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Generate the PDF
        pdf_content = generate_policy_document(policy)
        
        # Save to policy model
        policy.document = pdf_content
        policy.save(update_fields=['document'])
        
        return True
    except Exception as e:
        print(f"Error generating policy document: {str(e)}")
        return False
