import json
from django.views import View
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from .models_diy import DIYApplication

class CheckApplicationStatusView(View):
    """
    API endpoint to check the status of an application
    """
    def get(self, request, *args, **kwargs):
        try:
            application_id = request.GET.get('application_id')
            if not application_id:
                return JsonResponse(
                    {'error': 'Application ID is required'}, 
                    status=400
                )
            
            application = get_object_or_404(DIYApplication, id=application_id)
            
            return JsonResponse({
                'status': application.status,
                'status_display': application.get_status_display(),
                'created_at': application.created_at.isoformat(),
                'updated_at': application.updated_at.isoformat(),
                'step': application.step,
                'is_complete': application.status == 'submitted'
            })
            
        except Http404:
            return JsonResponse(
                {'error': 'Application not found'}, 
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'error': 'An error occurred while checking application status'}, 
                status=500
            )
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            application_id = data.get('application_id')
            
            if not application_id:
                return JsonResponse(
                    {'error': 'Application ID is required'}, 
                    status=400
                )
                
            application = get_object_or_404(DIYApplication, id=application_id)
            
            # In a real application, you might want to update the status
            # or perform additional checks here
            
            return JsonResponse({
                'status': application.status,
                'status_display': application.get_status_display(),
                'step': application.step,
                'is_complete': application.status == 'submitted',
                'can_continue': application.status != 'submitted',
                'next_step': self._get_next_step(application)
            })
            
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON data'}, 
                status=400
            )
        except Http404:
            return JsonResponse(
                {'error': 'Application not found'}, 
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'error': 'An error occurred while checking application status'}, 
                status=500
            )
    
    def _get_next_step(self, application):
        """Helper method to determine the next step in the application process"""
        if application.status == 'draft':
            return 'diy_personal_details'
        elif application.status == 'in_progress':
            return f'diy_step{application.step + 1}'
        elif application.status == 'submitted':
            return 'diy_confirmation'
        return 'diy_start'
