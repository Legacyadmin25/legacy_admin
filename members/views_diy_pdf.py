import os
from django.views import View
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from django.conf import settings
from .models_diy import DIYApplication


def _get_pisa():
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return None
    return pisa

class GeneratePDFView(View):
    """
    View to generate a PDF document for a DIY application
    """
    def get(self, request, *args, **kwargs):
        application_id = request.GET.get('application_id')

        pisa = _get_pisa()
        if pisa is None:
            return HttpResponse('PDF generation is not available on this server', status=503)
        
        if not application_id:
            return HttpResponse('Application ID is required', status=400)
        
        try:
            application = DIYApplication.objects.get(id=application_id)
        except (DIYApplication.DoesNotExist, ValueError):
            raise Http404("Application not found")
        
        # Get the template
        template = get_template('members/diy/pdf/application_summary.html')
        
        # Add application data to context
        context = {
            'application': application,
            'applicant': application.applicants.first(),
            'spouse': application.spouses.first(),
            'dependents': application.dependents.all(),
            'beneficiaries': application.beneficiaries.all(),
            'documents': application.documents.all(),
            'SITE_URL': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Render the template with context
        html = template.render(context)
        
        # Create a PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="application_{application_id}.pdf"'
        
        # Generate PDF
        pdf_status = pisa.CreatePDF(
            html,
            dest=response,
            link_callback=self.link_callback
        )
        
        if pdf_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        return response
    
    def link_callback(self, uri, rel):
        """
        Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
        """
        # Use short variable names
        sUrl = settings.STATIC_URL      # Typically /static/
        sRoot = settings.STATIC_ROOT    # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL       # Typically /media/
        mRoot = settings.MEDIA_ROOT     # Typically /home/userX/project_site/media

        # Convert URIs to absolute system paths
        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri  # Handle absolute uri (ie: http://some.tld/foo.png)


        # Make sure that file exists
        if not os.path.isfile(path):
            raise Exception(
                'media URI must start with %s or %s' % (sUrl, mUrl)
            )
        return path
