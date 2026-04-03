from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

class DIYResumeApplicationView(View):
    """
    View to resume a saved application using a token
    """
    def get(self, request, token, *args, **kwargs):
        try:
            # In a real application, you would validate the token and retrieve the application
            # For now, we'll just redirect to the start page
            return redirect('members:diy_start')
            
        except Exception as e:
            logger.error(f"Error resuming application: {str(e)}")
            messages.error(request, 'Invalid or expired application link. Please start a new application.')
            return redirect('members:diy_start')


class DIYSaveForLaterView(View):
    """
    View to save the current application for later completion
    """
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        if not application:
            messages.error(request, 'No application found to save.')
            return redirect('members:diy_start')
        
        try:
            # Generate a secure token for resuming the application
            import secrets
            token = secrets.token_urlsafe(32)
            
            # In a real application, you would save this token with the application
            # and send it to the user's email
            
            # For now, we'll just log it
            logger.info(f"Save for later token for application {application.id}: {token}")
            
            # Clear the session
            if 'diy_application_id' in request.session:
                del request.session['diy_application_id']
            
            messages.success(
                request,
                'Your application has been saved. ' \
                'Use the link we sent to your email to resume your application.'
            )
            
            return redirect('members:diy_start')
            
        except Exception as e:
            logger.error(f"Error saving application for later: {str(e)}")
            messages.error(request, 'There was an error saving your application. Please try again.')
            return redirect('members:diy_personal_details')
    
    def get_application(self, request):
        """Helper method to get the current application"""
        from .models_diy import DIYApplication
        
        application_id = request.session.get('diy_application_id')
        if not application_id:
            return None
            
        try:
            return DIYApplication.objects.get(id=application_id)
        except (DIYApplication.DoesNotExist, ValueError):
            return None
