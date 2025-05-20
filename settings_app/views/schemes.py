from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
import csv
from settings_app.models import SchemeDocument, Underwriter
from schemes.models import Scheme
from settings_app.forms import SchemeForm, SchemeDocumentForm
from settings_app.models import Branch
from django.contrib.auth.decorators import login_required


# ─── Scheme List View ───────────────────────────────────────────────────────
class SchemeListView(LoginRequiredMixin, ListView):
    model = Scheme
    template_name = 'settings_app/scheme_setup.html'
    context_object_name = 'schemes'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        branch = user.profile.branch if hasattr(user, 'profile') else None
        
        if user.is_superuser:
            return Scheme.objects.all()
        if user.groups.filter(name='Branch Owner').exists():
            return Scheme.objects.filter(branch=branch)
        return Scheme.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = SchemeForm()
        ctx['doc_form'] = SchemeDocumentForm()
        return ctx


# ─── Scheme Create View ───────────────────────────────────────────────────────
class SchemeCreateView(LoginRequiredMixin, CreateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('settings:scheme')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Scheme created successfully.")
        return redirect(self.success_url)


# ─── Scheme Update View ───────────────────────────────────────────────────────
class SchemeUpdateView(LoginRequiredMixin, UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('settings:scheme')

    def form_valid(self, form):
        messages.success(self.request, "Scheme updated successfully.")
        return super().form_valid(form)


# ─── Scheme Delete View ───────────────────────────────────────────────────────
class SchemeDeleteView(LoginRequiredMixin, DeleteView):
    model = Scheme
    success_url = reverse_lazy('settings:scheme')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Scheme deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ─── Upload Scheme Document ──────────────────────────────────────────────────
@login_required
def upload_scheme_document(request):
    if request.method == 'POST':
        form = SchemeDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.scheme_id = request.POST.get('scheme')
            doc.save()
            messages.success(request, "Document uploaded successfully.")
            return redirect('settings:scheme')
    return redirect('settings:scheme')


# ─── Delete Scheme Document ──────────────────────────────────────────────────
@login_required
def delete_scheme_document(request, pk):
    document = get_object_or_404(SchemeDocument, pk=pk)
    scheme_name = document.scheme.name if document.scheme else 'Unknown Scheme'
    document.delete()
    messages.success(request, f"Document deleted from {scheme_name}.")
    return redirect('settings:scheme')


# ─── Export Schemes to CSV ───────────────────────────────────────────────────
@login_required
def export_schemes_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="schemes.csv"'

    writer = csv.writer(response)
    writer.writerow(['Scheme Name', 'Scheme Number', 'Email', 'Telephone', 'Is Active'])

    for scheme in Scheme.objects.all():
        writer.writerow([
            scheme.name,
            scheme.scheme_number,
            scheme.email,
            scheme.telephone,
            'Yes' if scheme.is_active else 'No'
        ])

    return response


# ─── Scheme Assignment for Branch ───────────────────────────────────────────
@login_required
def assign_schemes_to_branch(request, branch_id):
    branch = get_object_or_404(Branch, pk=branch_id)
    
    if request.method == 'POST':
        selected_scheme_ids = request.POST.getlist('schemes')
        selected_schemes = Scheme.objects.filter(id__in=selected_scheme_ids)
        
        # Clear all existing schemes from the branch
        branch.schemes.clear()
        # Add the selected schemes to the branch
        branch.schemes.add(*selected_schemes)

        messages.success(request, f"{len(selected_schemes)} schemes assigned to branch '{branch.name}'.")
        return redirect('settings:branch')
    
    schemes = Scheme.objects.all()  # Fetch all schemes
    return render(request, 'settings_app/assign_schemes_to_branch.html', {
        'branch': branch,
        'schemes': schemes,
    })
