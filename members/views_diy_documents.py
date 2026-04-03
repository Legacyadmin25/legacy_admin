import os
import uuid
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from .models_diy import DIYApplication, DIYApplicationDocument

class UploadDocumentView(View):
    """
    API endpoint to handle document uploads for DIY applications
    """
    def post(self, request, *args, **kwargs):
        try:
            if 'document' not in request.FILES:
                return JsonResponse(
                    {'error': 'No document file provided'}, 
                    status=400
                )
            
            document_file = request.FILES['document']
            application_id = request.POST.get('application_id')
            document_type = request.POST.get('document_type', 'other')
            
            if not application_id:
                return JsonResponse(
                    {'error': 'Application ID is required'}, 
                    status=400
                )
            
            try:
                application = DIYApplication.objects.get(id=application_id)
            except (DIYApplication.DoesNotExist, ValueError):
                return JsonResponse(
                    {'error': 'Invalid application ID'}, 
                    status=400
                )
            
            # Validate file type
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
            ext = os.path.splitext(document_file.name)[1].lower()
            if ext not in valid_extensions:
                return JsonResponse(
                    {'error': f'Invalid file type. Allowed types: {valid_extensions}'}, 
                    status=400
                )
            
            # Generate a unique filename
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            filename = f"{application_id}_{document_type}_{timestamp}{ext}"
            
            # Save the file
            file_path = os.path.join('diy_documents', filename)
            saved_path = default_storage.save(file_path, ContentFile(document_file.read()))
            
            # Create document record
            document = DIYApplicationDocument.objects.create(
                application=application,
                document_type=document_type,
                file=saved_path,
                original_filename=document_file.name,
                file_size=document_file.size,
                mime_type=document_file.content_type
            )
            
            return JsonResponse({
                'id': str(document.id),
                'document_type': document.document_type,
                'file': document.file.url if document.file else None,
                'original_filename': document.original_filename,
                'uploaded_at': document.uploaded_at.isoformat(),
                'file_size': document.file_size
            })
            
        except Exception as e:
            return JsonResponse(
                {'error': f'Error uploading document: {str(e)}'}, 
                status=500
            )


class DeleteDocumentView(View):
    """
    API endpoint to delete uploaded documents
    """
    def post(self, request, *args, **kwargs):
        try:
            document_id = request.POST.get('document_id')
            
            if not document_id:
                return JsonResponse(
                    {'error': 'Document ID is required'}, 
                    status=400
                )
            
            try:
                document = DIYApplicationDocument.objects.get(id=document_id)
                
                # Delete the file from storage
                if document.file:
                    if default_storage.exists(document.file.name):
                        default_storage.delete(document.file.name)
                
                # Delete the document record
                document.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Document deleted successfully'
                })
                
            except DIYApplicationDocument.DoesNotExist:
                return JsonResponse(
                    {'error': 'Document not found'}, 
                    status=404
                )
                
        except Exception as e:
            return JsonResponse(
                {'error': f'Error deleting document: {str(e)}'}, 
                status=500
            )
