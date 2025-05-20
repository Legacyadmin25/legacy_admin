from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from settings_app.models import Underwriter
from settings_app.forms import UnderwriterForm
from django.http import HttpResponse
import csv
from django.contrib.auth.decorators import login_required  # <-- Add this import
from settings_app.forms import UnderwriterDocumentForm
from settings_app.models import UnderwriterDocument


# ─── Underwriter List View ───────────────────────────────────────────────────
class UnderwriterListView(LoginRequiredMixin, ListView):
    model = Underwriter
    template_name = 'settings_app/underwriter_setup.html'
    context_object_name = 'underwriters'
    ordering = ['-modified_date']

    def get_queryset(self):
        # You can add filtering logic based on user roles here if needed
        return Underwriter.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = UnderwriterForm()
        return ctx


# ─── Underwriter Create View ───────────────────────────────────────────────────
class UnderwriterCreateView(LoginRequiredMixin, CreateView):
    model = Underwriter
    form_class = UnderwriterForm
    template_name = 'settings_app/underwriter_setup.html'
    success_url = reverse_lazy('settings:underwriter')

    def form_valid(self, form):
        messages.success(self.request, "Underwriter created successfully.")
        return super().form_valid(form)


# ─── Underwriter Update View ───────────────────────────────────────────────────
class UnderwriterUpdateView(LoginRequiredMixin, UpdateView):
    model = Underwriter
    form_class = UnderwriterForm
    template_name = 'settings_app/underwriter_setup.html'
    success_url = reverse_lazy('settings:underwriter')

    def form_valid(self, form):
        messages.success(self.request, "Underwriter updated successfully.")
        return super().form_valid(form)


# ─── Underwriter Delete View ───────────────────────────────────────────────────
class UnderwriterDeleteView(LoginRequiredMixin, DeleteView):
    model = Underwriter
    template_name = 'settings_app/underwriter_confirm_delete.html'
    success_url = reverse_lazy('settings:underwriter')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Underwriter deleted.")
        return super().delete(request, *args, **kwargs)


# ─── Export Underwriters to CSV ───────────────────────────────────────────────
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
