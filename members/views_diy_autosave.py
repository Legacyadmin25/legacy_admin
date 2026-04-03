from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404, reverse
import json
import logging
from django.utils import timezone

from .models_incomplete import IncompleteApplication
from settings_app.models import Agent

logger = logging.getLogger(__name__)

@csrf_protect
@require_POST
def auto_save_application(request):
    """
    API endpoint to save form data automatically
    """
    try:
        data = json.loads(request.body)
        step = data.get('step')
        form_data = data.get('form_data', {})
        
        if not step or not isinstance(form_data, dict):
            return JsonResponse({'status': 'error', 'message': 'Invalid request data'}, status=400)
        
        # Get or create incomplete application
        token = request.session.get('incomplete_application_token')
        
        if token:
            try:
                incomplete_app = IncompleteApplication.objects.get(token=token)
            except IncompleteApplication.DoesNotExist:
                incomplete_app = None
        else:
            incomplete_app = None
        
        # If no existing application, create a new one
        if not incomplete_app:
            agent_id = request.session.get('diy_agent_id')
            agent = None
            scheme = None
            branch = None
            
            if agent_id:
                try:
                    agent = Agent.objects.get(pk=agent_id)
                    scheme = agent.scheme
                    branch = agent.scheme.branch if agent.scheme else None
                except Agent.DoesNotExist:
                    pass
            
            # Create new incomplete application
            incomplete_app = IncompleteApplication(
                agent=agent,
                scheme=scheme,
                branch=branch,
                current_step=step,
                session_key=request.session.session_key,
                user=request.user if request.user.is_authenticated else None,
                phone_number=form_data.get('phone_number', '')
            )
            incomplete_app.save()
            
            # Store token in session
            request.session['incomplete_application_token'] = str(incomplete_app.token)
        
        # Save form data for this step
        incomplete_app.save_step_data(step, form_data)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Data saved successfully',
            'token': str(incomplete_app.token),
            'timestamp': incomplete_app.updated_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in auto_save_application: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)


@csrf_protect
@require_POST
def mark_application_abandoned(request, token):
    """
    Mark an incomplete application as abandoned
    """
    try:
        incomplete_app = get_object_or_404(IncompleteApplication, token=token)
        
        # Security check - only allow if this application belongs to the current user/session
        if request.user.is_authenticated:
            if incomplete_app.user and incomplete_app.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        elif incomplete_app.session_key != request.session.session_key:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        incomplete_app.mark_abandoned()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Application marked as abandoned'
        })
        
    except Exception as e:
        logger.error(f"Error in mark_application_abandoned: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)


@csrf_protect
@require_POST
def mark_application_completed(request, token):
    """
    Mark an incomplete application as completed
    """
    try:
        incomplete_app = get_object_or_404(IncompleteApplication, token=token)
        
        # Security check - only allow if this application belongs to the current user/session
        if request.user.is_authenticated:
            if incomplete_app.user and incomplete_app.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        elif incomplete_app.session_key != request.session.session_key:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        incomplete_app.mark_completed()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Application marked as completed'
        })
        
    except Exception as e:
        logger.error(f"Error in mark_application_completed: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)


@csrf_protect
@require_GET
def check_application_exists(request, token):
    """
    Check if an incomplete application exists with the given token
    """
    try:
        try:
            incomplete_app = IncompleteApplication.objects.get(token=token, status='in_progress')
        except IncompleteApplication.DoesNotExist:
            return JsonResponse({
                'status': 'success',
                'exists': False
            })
        
        # Check if the application is associated with the current user or session
        user_match = request.user.is_authenticated and incomplete_app.user and incomplete_app.user == request.user
        session_match = incomplete_app.session_key == request.session.session_key
        
        # If neither user nor session matches, don't allow access
        if not (user_match or session_match):
            # For security, don't reveal that the application exists
            return JsonResponse({
                'status': 'success',
                'exists': False
            })
        
        # Calculate time since last update
        time_since_update = timezone.now() - incomplete_app.updated_at
        hours_since_update = time_since_update.total_seconds() / 3600
        
        # Generate resume URL
        resume_url = reverse('members:diy_resume_application', kwargs={'token': token})
        
        return JsonResponse({
            'status': 'success',
            'exists': True,
            'token': str(incomplete_app.token),
            'current_step': incomplete_app.current_step,
            'last_updated': incomplete_app.updated_at.isoformat(),
            'hours_since_update': round(hours_since_update, 1),
            'resume_url': resume_url
        })
        
    except Exception as e:
        logger.error(f"Error in check_application_exists: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)
