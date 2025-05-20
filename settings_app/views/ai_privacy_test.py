"""
AI Privacy Controls Test View

This module provides test views for demonstrating the AI privacy controls in action.
"""

import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from settings_app.models import AISettings, AIUserConsent, AIRequestLog
from settings_app.utils.ai_privacy import redact_pii, prepare_ai_prompt
from settings_app.utils.openai_helper import get_scheme_insights, get_branch_insights

logger = logging.getLogger(__name__)


@login_required
def ai_privacy_dashboard(request):
    """
    Dashboard for testing and demonstrating AI privacy controls
    """
    # Get AI settings
    ai_settings = AISettings.get_settings()
    
    # Get or create user consent
    user_consent, created = AIUserConsent.objects.get_or_create(
        user=request.user,
        defaults={
            'search_consent': False,
            'insight_consent': False,
            'suggestion_consent': False
        }
    )
    
    # Get recent AI request logs
    recent_logs = AIRequestLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    context = {
        'ai_settings': ai_settings,
        'user_consent': user_consent,
        'recent_logs': recent_logs,
        'page_title': 'AI Privacy Controls'
    }
    
    return render(request, 'settings_app/ai_privacy_dashboard.html', context)


@login_required
@require_POST
def update_ai_consent(request):
    """
    Update user's AI consent settings
    """
    try:
        # Get consent values from form
        search_consent = request.POST.get('search_consent') == 'on'
        insight_consent = request.POST.get('insight_consent') == 'on'
        suggestion_consent = request.POST.get('suggestion_consent') == 'on'
        
        # Update user consent
        user_consent, created = AIUserConsent.objects.update_or_create(
            user=request.user,
            defaults={
                'search_consent': search_consent,
                'insight_consent': insight_consent,
                'suggestion_consent': suggestion_consent
            }
        )
        
        messages.success(request, 'AI consent preferences updated successfully.')
        
    except Exception as e:
        logger.error(f"Error updating AI consent: {str(e)}")
        messages.error(request, f"Error updating AI consent: {str(e)}")
    
    return redirect('ai_privacy_dashboard')


@login_required
@require_POST
def test_redact_pii(request):
    """
    Test the PII redaction functionality
    """
    try:
        text = request.POST.get('text', '')
        redacted_text = redact_pii(text)
        
        return JsonResponse({
            'original': text,
            'redacted': redacted_text,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in PII redaction test: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'success': False
        })


@login_required
@require_POST
def test_ai_insight(request):
    """
    Test the AI insights functionality with privacy controls
    """
    try:
        # Check if user has consented to insights
        user_consent = AIUserConsent.objects.filter(user=request.user).first()
        if not user_consent or not user_consent.insight_consent:
            return JsonResponse({
                'error': 'You have not provided consent for AI-powered insights. Please update your preferences.',
                'success': False
            })
        
        insight_type = request.POST.get('insight_type')
        question = request.POST.get('question', '')
        object_id = request.POST.get('object_id')
        
        if not question or not insight_type or not object_id:
            return JsonResponse({
                'error': 'Missing required parameters',
                'success': False
            })
        
        # Get the appropriate object based on insight type
        if insight_type == 'scheme':
            from schemes.models import Scheme
            obj = Scheme.objects.get(id=object_id)
            insight = get_scheme_insights(obj, question, user=request.user)
        elif insight_type == 'branch':
            from branches.models import Branch
            obj = Branch.objects.get(id=object_id)
            insight = get_branch_insights(obj, question, user=request.user)
        else:
            return JsonResponse({
                'error': 'Invalid insight type',
                'success': False
            })
        
        # Log the successful test
        AIRequestLog.objects.create(
            user=request.user,
            action='test_insight',
            prompt_summary=f"Test {insight_type} insight: {question[:50]}...",
            model_used=AISettings.get_settings().default_model,
            response_status=True
        )
        
        return JsonResponse({
            'insight': insight,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in AI insight test: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'success': False
        })
