import json
import logging
from decimal import Decimal

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from settings_app.utils.openai_helper import suggest_tiers_from_description, format_suggested_tiers

logger = logging.getLogger(__name__)

@login_required
@require_POST
def suggest_tiers(request):
    """
    API endpoint to suggest tiers based on plan description.
    Expects JSON data with plan_name, description, policy_type, and premium.
    Returns JSON with suggested tiers.
    """
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        plan_name = data.get('plan_name', '')
        description = data.get('description', '')
        policy_type = data.get('policy_type', 'service')
        premium = data.get('premium', '0')
        
        # Validate required fields
        if not description:
            return JsonResponse({'error': 'Plan description is required'}, status=400)
        
        # Convert premium to float for the API call
        try:
            premium_float = float(Decimal(str(premium).replace('R', '').replace(',', '') or '0'))
        except (ValueError, TypeError):
            premium_float = 0.0
        
        # Get tier suggestions from OpenAI
        raw_suggestions = suggest_tiers_from_description(
            plan_name, description, policy_type, premium_float
        )
        
        # Format the suggestions for the form
        suggested_tiers = format_suggested_tiers(raw_suggestions)
        
        # Return the suggestions
        return JsonResponse({
            'success': True,
            'tiers': suggested_tiers,
            'message': f"Generated {len(suggested_tiers)} tier suggestions based on the plan description."
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error suggesting tiers: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
