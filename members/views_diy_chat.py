import json
import logging
from django.views import View
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models_diy import DIYApplication
from .utils.plan_chat import get_plan_answer  # Assuming this is the corrected version

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DIYChatView(View):
    """
    View to handle AI chat functionality for DIY applications
    """
    def get(self, request, application_id, *args, **kwargs):
        """
        Get chat history for an application
        """
        try:
            application = get_object_or_404(
                DIYApplication,
                id=application_id,
                user=request.user  # Ensure user can only access their own applications
            )
            
            # In a real implementation, you would retrieve chat history from a database
            # For now, return a sample response
            return JsonResponse({
                'status': 'success',
                'messages': application.chat_messages if hasattr(application, 'chat_messages') else []
            })
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
            return JsonResponse(
                {'error': 'An error occurred while retrieving chat history'},
                status=500
            )
    
    def post(self, request, application_id, *args, **kwargs):
        """
        Process a new chat message
        """
        try:
            # Get the application
            application = get_object_or_404(
                DIYApplication,
                id=application_id,
                user=request.user  # Ensure user can only access their own applications
            )
            
            # Parse the request data
            try:
                data = json.loads(request.body)
                message = data.get('message', '').strip()
                
                if not message:
                    return JsonResponse(
                        {'error': 'Message cannot be empty'},
                        status=400
                    )
                    
                # Get the plan and tiers for context
                plan = application.plan
                tiers = application.tiers.all() if hasattr(application, 'tiers') else []
                
                # Get AI response
                response = get_plan_answer(message, plan, tiers)
                
                # In a real implementation, you would save the chat messages to a database
                # For now, we'll just return the response
                
                return JsonResponse({
                    'status': 'success',
                    'response': response,
                    'suggested_questions': self._get_suggested_questions()
                })
                
            except json.JSONDecodeError:
                return JsonResponse(
                    {'error': 'Invalid JSON data'},
                    status=400
                )
                
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return JsonResponse(
                {'error': 'An error occurred while processing your message'},
                status=500
            )
    
    def _get_suggested_questions(self):
        """
        Get a list of suggested questions for the user
        """
        return [
            "What does this plan cover?",
            "What are the benefits of this plan?",
            "How do I make a claim?",
            "What is the waiting period?",
            "Can I add dependents later?"
        ]
