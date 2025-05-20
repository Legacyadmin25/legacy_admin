"""
AI Summary functionality for policy profiles

This module provides views and utilities for generating AI-powered summaries
of policy data, offering users plain-language insights about policies.
"""

import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.shortcuts import get_object_or_404

from members.models import Policy
from settings_app.models import AIRequestLog, AIUserConsent
from settings_app.utils.ai_privacy import redact_pii, prepare_ai_prompt
from settings_app.models import UserRole

logger = logging.getLogger(__name__)

@login_required
@require_POST
def generate_policy_summary(request, policy_id):
    """
    Generate an AI-powered summary of a policy.
    
    This view takes a policy ID, retrieves the policy data, and sends it to OpenAI
    to generate a plain-language summary of the policy status, family structure,
    lapse risk, and payment behavior.
    
    Access is restricted to internal_admin and scheme_manager roles only.
    """
    # Check user role - only internal_admin and scheme_manager can use this feature
    try:
        user_role = request.user.role.role_type
        if user_role not in ['internal_admin', 'scheme_manager']:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to use the AI Summary feature.'
            })
    except (UserRole.DoesNotExist, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to use the AI Summary feature.'
        })
    
    # Check if user has consented to AI summary
    try:
        user_consent = AIUserConsent.objects.filter(user=request.user).first()
        if not user_consent or not user_consent.summary_consent:
            return JsonResponse({
                'success': False,
                'error': 'You have not provided consent for AI-powered summaries. Please update your preferences in the AI Privacy Controls.'
            })
    except Exception as e:
        logger.error(f"Error checking AI consent: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error checking AI consent. Please try again later.'
        })
    
    # Get the policy
    try:
        policy = get_object_or_404(Policy, id=policy_id)
    except Exception as e:
        logger.error(f"Error retrieving policy: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error retrieving policy data. Please try again later.'
        })
    
    try:
        # Prepare policy data for the AI
        # Use anonymized identifiers instead of actual names/IDs
        policy_data = {
            'policy_id': f"POLICY_{policy.id}",  # Anonymized ID
            'status': policy.status,
            'start_date': policy.start_date.strftime('%Y-%m-%d') if policy.start_date else None,
            'plan': policy.plan.name if policy.plan else None,
            'cover_amount': policy.cover_amount,
            'premium': policy.premium,
            'payment_method': policy.payment_method,
            'payment_day': policy.payment_day,
            'last_payment_date': policy.last_payment_date.strftime('%Y-%m-%d') if policy.last_payment_date else None,
            'last_payment_amount': policy.last_payment_amount,
            'lapse_reason': policy.lapse_reason,
            'has_spouse': policy.member.spouse is not None if policy.member else False,
            'dependent_count': policy.member.dependents.count() if policy.member else 0,
            'beneficiary_count': policy.beneficiaries.count(),
            'branch': policy.branch.name if policy.branch else None,
            'scheme': policy.scheme.name if policy.scheme else None,
        }
        
        # Log the AI request
        log_entry = AIRequestLog.objects.create(
            user=request.user,
            action='summary',
            prompt_summary=f"AI summary for policy {policy_data['policy_id']}",
            model_used=getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4o'),
            response_status=True
        )
        
        # Call OpenAI to generate the summary
        import openai
        
        # Get API key from settings
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            logger.error("OpenAI API key not found in settings")
            return JsonResponse({
                'success': False,
                'error': 'OpenAI API key not configured. Please contact the administrator.'
            })
        
        # Prepare the system prompt
        system_prompt = """
        You are an assistant generating plain-language summaries of funeral policy data.
        
        Your task is to analyze the policy data and provide a clear, concise summary that covers:
        1. Policy status and basic details
        2. Family structure (main member, spouse, dependents)
        3. Payment behavior and history
        4. Lapse risk assessment (if applicable)
        5. Any notable aspects of the policy
        
        Write in a professional but conversational tone. Use bullet points where appropriate.
        Focus on the most important information that would help an administrator understand the policy at a glance.
        
        IMPORTANT: Never include any personally identifiable information (PII) in your response.
        Do not make up information that is not provided in the data.
        If certain information is missing, simply note that it's not available.
        
        Format your response in markdown for better readability.
        """
        
        # Call OpenAI API
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(policy_data)}
            ],
            temperature=0.3,  # Lower temperature for more factual responses
            max_tokens=800,
            user="anonymous"  # Ensure OpenAI doesn't use our data for training
        )
        
        # Extract the response
        ai_response = response.choices[0].message.content.strip()
        
        # Add disclaimer
        disclaimer = """
        
        ---
        
        *This summary was generated by AI and may not be 100% accurate. Always verify important information directly in the policy details.*
        """
        
        summary = ai_response + disclaimer
        
        # Update the log entry with success
        log_entry.response_status = True
        log_entry.save()
        
        return JsonResponse({
            'success': True,
            'summary': summary
        })
            
    except Exception as e:
        logger.exception(f"Error generating AI summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })
