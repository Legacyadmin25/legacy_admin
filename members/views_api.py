import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from schemes.models import Plan
from settings_app.models import PlanMemberTier
from .utils.ocr_processor import process_id_document
from .utils.plan_chat import get_plan_answer

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def process_id_document_api(request):
    """
    API endpoint to process an ID document and extract information
    """
    try:
        data = json.loads(request.body)
        image_data = data.get('image_data')
        
        if not image_data:
            return JsonResponse({'error': 'No image data provided'}, status=400)
        
        # Process the document
        result = process_id_document(image_data)
        
        if result.get('error'):
            return JsonResponse({'error': result['error']}, status=400)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id_number': result.get('id_number'),
                'full_name': result.get('full_name'),
                'date_of_birth': result.get('date_of_birth'),
                'gender': result.get('gender')
            }
        })
    except Exception as e:
        logger.error(f"Error processing ID document: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def plan_chat_api(request):
    """
    API endpoint to answer questions about a plan
    """
    try:
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        question = data.get('question')
        
        if not plan_id:
            return JsonResponse({'error': 'No plan ID provided'}, status=400)
        
        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)
        
        # Get the plan
        plan = get_object_or_404(Plan, id=plan_id)
        
        # Get the tiers for the plan
        tiers = PlanMemberTier.objects.filter(plan=plan)
        
        # Get the answer
        answer = get_plan_answer(question, plan, tiers)
        
        return JsonResponse({
            'success': True,
            'answer': answer
        })
    except Exception as e:
        logger.error(f"Error getting plan answer: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
