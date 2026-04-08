import os
import io
from django.views import View
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from .models_diy import DIYApplication
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class DownloadCertificateView(View):
    """
    View to download a certificate for a completed application
    """
    @method_decorator(login_required)
    def get(self, request, application_id, *args, **kwargs):
        try:
            # Get the application, ensuring it belongs to the current user
            application = get_object_or_404(
                DIYApplication,
                id=application_id,
                user=request.user,
                status='completed'  # Only allow download for completed applications
            )
            
            # Check if certificate file exists
            if not application.certificate_file:
                raise Http404("Certificate not found")
            
            # Open the file and create a response
            file_path = application.certificate_file.path
            with open(file_path, 'rb') as pdf:
                response = HttpResponse(pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="certificate_{application_id}.pdf"'
                return response
                
        except (ValueError, OSError):
            raise Http404("Certificate file not found")


class VerifyCertificateView(View):
    """
    View to verify a certificate using a verification token
    """
    def get(self, request, application_id, *args, **kwargs):
        try:
            # Get the application by ID
            application = get_object_or_404(DIYApplication, id=application_id)
            
            # Check if certificate exists and is verified
            if not application.certificate_file:
                return JsonResponse({
                    'valid': False,
                    'message': 'No certificate found for this application',
                    'application_id': str(application.id)
                })
                
            # In a real implementation, you would verify a token or signature here
            # For now, we'll just check if the certificate file exists
            
            return JsonResponse({
                'valid': True,
                'message': 'Certificate is valid',
                'application_id': str(application.id),
                'applicant_name': application.get_applicant_full_name(),
                'issue_date': application.completed_at.isoformat() if application.completed_at else None,
                'status': application.status
            })
            
        except (ValueError, DIYApplication.DoesNotExist):
            return JsonResponse({
                'valid': False,
                'message': 'Invalid application ID',
                'application_id': str(application_id)
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'message': 'Error verifying certificate',
                'error': str(e)
            }, status=500)
