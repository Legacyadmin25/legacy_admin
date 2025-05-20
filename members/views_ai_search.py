"""
AI-Powered Search Assistant for the Find Policy System

This module provides views and utilities for the AI-powered search functionality,
allowing users to search for policies using natural language queries.
"""

import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings

from settings_app.models import AIRequestLog, AIUserConsent
from settings_app.utils.ai_privacy import redact_pii, prepare_ai_prompt
from settings_app.models import UserRole

logger = logging.getLogger(__name__)

@login_required
@require_POST
def ai_search_assistant(request):
    """
    Process a natural language query and convert it to search filters.
    
    This view takes a natural language query from the user, sends it to OpenAI
    to convert it into structured search filters, and returns those filters
    as a JSON response.
    
    Access is restricted to internal_admin and scheme_manager roles only.
    """
    # Check user role - only internal_admin and scheme_manager can use this feature
    try:
        user_role = request.user.role.role_type
        if user_role not in ['internal_admin', 'scheme_manager']:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to use the AI Search Assistant.'
            })
    except (UserRole.DoesNotExist, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to use the AI Search Assistant.'
        })
    
    # Check if user has consented to AI search
    try:
        user_consent = AIUserConsent.objects.filter(user=request.user).first()
        if not user_consent or not user_consent.search_consent:
            return JsonResponse({
                'success': False,
                'error': 'You have not provided consent for AI-powered search. Please update your preferences in the AI Privacy Controls.'
            })
    except Exception as e:
        logger.error(f"Error checking AI consent: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error checking AI consent. Please try again later.'
        })
    
    # Get the natural language query
    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Please provide a search query.'
        })
    
    # Redact any PII from the query
    safe_query = redact_pii(query)
    
    try:
        # Log the AI request
        log_entry = AIRequestLog.objects.create(
            user=request.user,
            action='search',
            prompt_summary=f"AI search: {safe_query[:50]}...",
            model_used=getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4o'),
            response_status=True
        )
        
        # Call OpenAI to convert the query to filters
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
        You are an assistant converting natural-language queries into search filters for a funeral policy system.
        
        Your task is to analyze the user's query and extract search parameters that can be used in a Django ORM query.
        Return ONLY a JSON object with the extracted filters. Do not include any explanations or additional text.
        
        Available filter fields:
        - status: "active", "lapsed", "trial"
        - payment_method: "DEBIT_ORDER", "EFT", "EASYPAY"
        - branch__name: Name of the branch
        - scheme__name: Name of the scheme
        - plan__name: Name of the plan
        - start_date__gte: Start date greater than or equal (format: YYYY-MM-DD)
        - start_date__lte: Start date less than or equal (format: YYYY-MM-DD)
        - cover_amount__gte: Minimum cover amount
        - cover_amount__lte: Maximum cover amount
        - premium__gte: Minimum premium
        - premium__lte: Maximum premium
        - member__dependents__isnull: False to find policies with dependents
        - member__spouse__isnull: False to find policies with a spouse
        
        For date filters, use the current year if the user mentions "this year".
        For relative time periods like "last 3 months", calculate the appropriate date.
        
        Example query: "Find all lapsed policies with EasyPay payments who joined this year"
        Example response: {"status": "lapsed", "payment_method": "EASYPAY", "start_date__gte": "2025-01-01"}
        
        IMPORTANT: Never include any personally identifiable information (PII) in your response.
        """
        
        # Call OpenAI API
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": safe_query}
            ],
            temperature=0.2,  # Lower temperature for more deterministic responses
            max_tokens=500,
            user="anonymous"  # Ensure OpenAI doesn't use our data for training
        )
        
        # Extract the response
        ai_response = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            filters = json.loads(ai_response)
            
            # Create a human-readable description of the filters
            filter_descriptions = []
            for key, value in filters.items():
                if key == 'status':
                    filter_descriptions.append(f"status = {value}")
                elif key == 'payment_method':
                    payment_method_map = {
                        'DEBIT_ORDER': 'Debit Order',
                        'EFT': 'EFT',
                        'EASYPAY': 'Easypay'
                    }
                    display_value = payment_method_map.get(value, value)
                    filter_descriptions.append(f"payment method = {display_value}")
                elif key == 'branch__name':
                    filter_descriptions.append(f"branch = {value}")
                elif key == 'scheme__name':
                    filter_descriptions.append(f"scheme = {value}")
                elif key == 'plan__name':
                    filter_descriptions.append(f"plan = {value}")
                elif key == 'start_date__gte':
                    filter_descriptions.append(f"joined after {value}")
                elif key == 'start_date__lte':
                    filter_descriptions.append(f"joined before {value}")
                elif key == 'cover_amount__gte':
                    filter_descriptions.append(f"minimum cover = R{value}")
                elif key == 'cover_amount__lte':
                    filter_descriptions.append(f"maximum cover = R{value}")
                elif key == 'premium__gte':
                    filter_descriptions.append(f"minimum premium = R{value}")
                elif key == 'premium__lte':
                    filter_descriptions.append(f"maximum premium = R{value}")
                elif key == 'member__dependents__isnull' and value is False:
                    filter_descriptions.append("has dependents")
                elif key == 'member__spouse__isnull' and value is False:
                    filter_descriptions.append("has spouse")
                elif key == 'member__spouse__isnull' and value is True:
                    filter_descriptions.append("no spouse")
                else:
                    filter_descriptions.append(f"{key.replace('__', ' ')} = {value}")
            
            filter_description = "Filters applied: " + ", ".join(filter_descriptions)
            
            # Update the log entry with success
            log_entry.response_status = True
            log_entry.save()
            
            return JsonResponse({
                'success': True,
                'filters': filters,
                'filter_description': filter_description
            })
            
        except json.JSONDecodeError:
            logger.error(f"Error parsing OpenAI response as JSON: {ai_response}")
            return JsonResponse({
                'success': False,
                'error': 'Error parsing AI response. Please try a different query.'
            })
            
    except Exception as e:
        logger.exception(f"Error in AI search assistant: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })
