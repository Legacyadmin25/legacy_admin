from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from settings_app.models import Underwriter
from settings_app.forms import UnderwriterForm
from django.http import HttpResponse, JsonResponse
import csv
import json
from django.contrib.auth.decorators import login_required  
from settings_app.forms import UnderwriterDocumentForm
from settings_app.models import UnderwriterDocument
import pandas as pd
import io
from datetime import datetime


# ─── Underwriter List View ────────────────────────────────────────────
class UnderwriterListView(LoginRequiredMixin, ListView):
    model = Underwriter
    template_name = 'settings_app/underwriter_setup.html'
    context_object_name = 'underwriters'
    paginate_by = 10  
    
    def get_queryset(self):
        queryset = Underwriter.objects.all()
        
        # Search functionality
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                name__icontains=search_query
            ) | queryset.filter(
                fsp_number__icontains=search_query
            ) | queryset.filter(
                email__icontains=search_query
            ) | queryset.filter(
                contact_person__icontains=search_query
            )
        
        # Sorting functionality
        sort = self.request.GET.get('sort', 'modified_date')
        sort_dir = self.request.GET.get('dir', 'desc')
        
        # Validate sort field to prevent injection
        valid_sort_fields = ['name', 'fsp_number', 'email', 'contact_person', 'modified_date']
        if sort not in valid_sort_fields:
            sort = 'modified_date'
            
        # Apply sorting direction
        if sort_dir == 'asc':
            ordering = sort
        else:
            ordering = f'-{sort}'
            
        return queryset.order_by(ordering)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = UnderwriterForm()
        
        # Add search and sort params to context for the template
        ctx['search_query'] = self.request.GET.get('q', '')
        ctx['current_sort'] = self.request.GET.get('sort', 'modified_date')
        ctx['current_sort_dir'] = self.request.GET.get('dir', 'desc')
        ctx['is_htmx'] = self.request.headers.get('HX-Request') == 'true'
        
        return ctx


# ─── Underwriter Create View ───────────────────────────────────────────────────
class UnderwriterCreateView(LoginRequiredMixin, CreateView):
    model = Underwriter
    form_class = UnderwriterForm
    template_name = 'settings_app/underwriter_form_content.html'
    success_url = reverse_lazy('settings:underwriter')

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        return render(request, self.template_name, {'form': form})

    def form_valid(self, form):
        self.object = form.save()
        success_message = f"Underwriter '{self.object.name}' created successfully."
        messages.success(self.request, success_message)
        
        is_htmx = self.request.headers.get('HX-Request') == 'true'
        
        if is_htmx:
            # For HTMX, return a partial response
            response = render(
                self.request,
                'settings_app/underwriter_form_content.html',
                self.get_context_data(form=form, success=True)
            )
            
            # Trigger an event to refresh the underwriter list with additional details
            response['HX-Trigger'] = json.dumps({
                'underwriterSaved': {
                    'message': success_message,
                    'type': 'success',
                    'title': 'Success',
                    'underwriterId': self.object.id
                }
            })
            return response
        
        # For regular form submissions, return the normal redirect
        return redirect(self.success_url)
        
    def form_invalid(self, form):
        is_htmx = self.request.headers.get('HX-Request') == 'true'
        
        if is_htmx:
            # For HTMX, return the form with errors
            context = self.get_context_data(form=form)
            
            # Convert form errors to a structured format for the frontend
            field_errors = {}
            for field_name, error_list in form.errors.items():
                if field_name != '__all__':  # Skip non-field errors
                    field_errors[field_name] = error_list[0] if error_list else ''
            
            # Check if the client is expecting JSON
            content_type = self.request.headers.get('Content-Type', '')
            if 'application/json' in content_type or self.request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'fieldErrors': field_errors,
                    'nonFieldErrors': [str(e) for e in form.non_field_errors()]
                }, status=400)
                
            # Add errors to context for template rendering
            context['field_errors'] = field_errors
            
            # Return form with validation errors
            return render(
                self.request,
                self.template_name,
                context,
                status=422  # Unprocessable Entity for validation errors
            )
        
        # For regular form submissions, return the normal form with errors
        return super().form_invalid(form)


# ─── Underwriter Update View ───────────────────────────────────────────────────
class UnderwriterUpdateView(LoginRequiredMixin, UpdateView):
    model = Underwriter
    form_class = UnderwriterForm
    template_name = 'settings_app/underwriter_form_content.html'
    success_url = reverse_lazy('settings:underwriter')
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        return render(request, self.template_name, {
            'form': form,
            'underwriter': self.object,
        })

    def form_valid(self, form):
        is_htmx = self.request.headers.get('HX-Request') == 'true'
        
        # Handle logo removal if requested
        if 'remove_logo' in self.request.POST:
            form.instance.logo = None
        
        # Save the form
        self.object = form.save()
        
        # Add success message
        messages.success(self.request, "Underwriter updated successfully.")
        
        if is_htmx:
            # Return a success response for HTMX
            response = HttpResponse(status=204)  # No content, success
            response['HX-Trigger'] = 'underwriterSaved'
            return response
        
        # For regular form submissions, return the normal redirect
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        is_htmx = self.request.headers.get('HX-Request') == 'true'
        
        if is_htmx:
            # For HTMX, return the form with errors
            context = self.get_context_data(form=form)
            
            # Convert form errors to a structured format for the frontend
            field_errors = {}
            for field_name, error_list in form.errors.items():
                if field_name != '__all__':  # Skip non-field errors
                    field_errors[field_name] = error_list[0] if error_list else ''
            
            # Check if the client is expecting JSON
            content_type = self.request.headers.get('Content-Type', '')
            if 'application/json' in content_type or self.request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'fieldErrors': field_errors,
                    'nonFieldErrors': [str(e) for e in form.non_field_errors()]
                }, status=400)
                
            # Add errors to context for template rendering
            context['field_errors'] = field_errors
            
            # Return form with validation errors
            return render(
                self.request,
                self.template_name,
                context,
                status=422  # Unprocessable Entity for validation errors
            )
        
        # For regular form submissions, return the normal form with errors
        return super().form_invalid(form)


# ─── Underwriter Delete View ────────────────────────────────────────────
class UnderwriterDeleteView(LoginRequiredMixin, DeleteView):
    model = Underwriter
    template_name = 'settings_app/underwriter_confirm_delete.html'
    success_url = reverse_lazy('settings:underwriter')

    def delete(self, request, *args, **kwargs):
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        try:
            self.object = self.get_object()
            underwriter_name = self.object.name
            
            # Check if underwriter is referenced by any plans before deleting
            from schemes.models import Plan
            plan_count = Plan.objects.filter(underwriter=self.object).count()
            
            if plan_count > 0:
                error_message = f"Cannot delete underwriter '{underwriter_name}' because it is used by {plan_count} plan(s)."
                
                if is_htmx:
                    return JsonResponse({
                        'message': error_message,
                        'title': 'Deletion Failed',
                        'type': 'error'
                    }, status=409)  # Conflict status code
                
                messages.error(self.request, error_message)
                return redirect(self.success_url)
            
            # If no references found, proceed with deletion
            self.object.delete()
            
            # Add success message
            success_message = f"Underwriter '{underwriter_name}' deleted successfully."
            messages.success(self.request, success_message)
            
            if is_htmx:
                # Return a success response for HTMX
                response = JsonResponse({
                    'message': success_message,
                    'title': 'Success',
                    'type': 'success'
                }, status=200)
                response['HX-Trigger'] = 'underwriterDeleted'
                return response
            
            # For regular requests, redirect to success URL
            return redirect(self.success_url)
            
        except Exception as e:
            error_message = f"Error deleting underwriter: {str(e)}"
            
            if is_htmx:
                # Check if it's a database constraint error
                if 'protected' in str(e).lower() or 'constraint' in str(e).lower() or 'foreign key' in str(e).lower():
                    constraint_message = f"Cannot delete underwriter '{self.get_object().name}' because it is in use by plans or policies."
                    return JsonResponse({
                        'message': constraint_message,
                        'title': 'Deletion Failed',
                        'type': 'error'
                    }, status=409)  # Conflict status code
                
                # Generic error response
                return JsonResponse({
                    'message': error_message,
                    'title': 'Error',
                    'type': 'error'
                }, status=500)
            
            # For regular requests, show error message and redirect
            messages.error(self.request, error_message)
            return redirect(self.success_url)


# ─── Export Underwriters to CSV ─────────────────────────────────────
@login_required
def export_underwriters_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="underwriters.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'FSP Number', 'Contact Person', 'Contact Number', 'Email'])
    
    for underwriter in Underwriter.objects.all():
        writer.writerow([
            underwriter.name,
            underwriter.fsp_number,
            underwriter.contact_person,
            underwriter.contact_number,
            underwriter.email
        ])

    return response


# ─── Underwriter Search View ────────────────────────────────────────────
@login_required
def underwriter_search(request):
    q = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')
    
    if sort_by not in ['name', 'fsp_number', 'email', 'contact_person']:
        sort_by = 'name'
    
    # Add '-' prefix for descending order if needed
    if request.GET.get('order') == 'desc':
        sort_by = f'-{sort_by}'
    
    underwriters = Underwriter.objects.order_by(sort_by)
    
    if q:
        underwriters = underwriters.filter(
            Q(name__icontains=q) |
            Q(fsp_number__icontains=q) |
            Q(email__icontains=q) |
            Q(contact_person__icontains=q)
        )
    
    # Handle pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(underwriters, 10)  # Show 10 underwriters per page
    
    try:
        underwriters_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        underwriters_page = paginator.page(1)
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'settings_app/underwriter_list_content.html', {
            'underwriters': underwriters_page,
            'current_sort': sort_by.replace('-', ''),
            'sort_order': 'desc' if sort_by.startswith('-') else 'asc',
            'query': q,
        })
    
    return render(request, 'settings_app/underwriter_list.html', {
        'underwriters': underwriters_page,
        'current_sort': sort_by.replace('-', ''),
        'sort_order': 'desc' if sort_by.startswith('-') else 'asc',
        'query': q,
    })


# ─── Underwriter API Endpoints ─────────────────────────────────────────
@login_required
def get_underwriter_details(request):
    """API endpoint to get underwriter details for plan form integration"""
    underwriter_id = request.GET.get('underwriter', None)
    
    if not underwriter_id:
        return JsonResponse({'error': 'No underwriter ID provided'}, status=400)
    
    try:
        underwriter = Underwriter.objects.get(pk=underwriter_id)
        data = {
            'id': underwriter.id,
            'name': underwriter.name,
            'fsp_number': underwriter.fsp_number,
            'email': underwriter.email,
            'contact_person': underwriter.contact_person,
            'phone': underwriter.phone,
            'logo_url': underwriter.logo.url if underwriter.logo else None,
        }
        
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'settings_app/underwriter_details_snippet.html', {
                'underwriter': underwriter
            })
        else:
            return JsonResponse(data)
            
    except Underwriter.DoesNotExist:
        return JsonResponse({'error': 'Underwriter not found'}, status=404)


# ─── Underwriter Document Management (Optional) ───────────────────────────────
@login_required
def upload_underwriter_document(request, underwriter_id):
    underwriter = get_object_or_404(Underwriter, pk=underwriter_id)
    if request.method == 'POST':
        form = UnderwriterDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.underwriter = underwriter
            doc.save()
            messages.success(request, f"Document uploaded for underwriter {underwriter.name}.")
            return redirect('settings:underwriter')
    return redirect('settings:underwriter')


@login_required
def delete_underwriter_document(request, document_id):
    document = get_object_or_404(UnderwriterDocument, pk=document_id)
    underwriter_name = document.underwriter.name if document.underwriter else 'Unknown Underwriter'
    document.delete()
    messages.success(request, f"Document deleted from underwriter {underwriter_name}.")
    return redirect('settings:underwriter')


# ─── Underwriter Template Download ──────────────────────────────────
@login_required
def underwriter_template_download(request):
    """Generate and download a template Excel file for underwriter imports"""
    
    # Create sample data
    sample_data = [
        ['ABC Insurance', '12345', 'True', 'John Smith', 'jsmith@example.com', '(123) 456-7890'],
        ['XYZ Underwriters', '67890', 'True', 'Jane Doe', 'jdoe@example.com', '(098) 765-4321']
    ]
    
    # Create DataFrame with columns matching the resource fields
    df = pd.DataFrame(sample_data, columns=[
        'name', 'fsp_number', 'is_active', 'contact_person', 'email', 'contact_number'
    ])
    
    # Create a buffer to hold the Excel file
    buffer = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Underwriter Template', index=False)
        
        # Get the worksheet and set column widths
        worksheet = writer.sheets['Underwriter Template']
        worksheet.set_column('A:A', 20)  # name
        worksheet.set_column('B:B', 12)  # fsp_number
        worksheet.set_column('C:C', 10)  # is_active
        worksheet.set_column('D:D', 20)  # contact_person
        worksheet.set_column('E:E', 25)  # email
        worksheet.set_column('F:F', 15)  # contact_number
        
        # Add instructions sheet
        instructions = pd.DataFrame([
            ['Instructions for importing underwriters:'],
            ['1. Fill in the data in the "Underwriter Template" sheet.'],
            ['2. Required fields: name, fsp_number, is_active (True/False)'],
            ['3. Optional fields: contact_person, email, contact_number'],
            ['4. Save the file and upload it using the Import Underwriters function.'],
            [''],
            ['Note: Existing underwriters with the same name will be updated.']
        ])
        instructions.to_excel(writer, sheet_name='Instructions', header=False, index=False)
        worksheet = writer.sheets['Instructions']
        worksheet.set_column('A:A', 70)
    
    # Set up the response
    buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f'underwriter_template_{timestamp}.xlsx'
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
