from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse
from settings_app.models import Branch
from schemes.models import Scheme
from settings_app.forms import BranchForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required  # <-- Add this import
import csv

# ─── Branch List View ───────────────────────────────────────────────────────
class BranchListView(LoginRequiredMixin, ListView):
    model = Branch
    template_name = 'settings_app/branch_setup.html'
    context_object_name = 'branches'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BranchForm()
        context['edit_mode'] = False
        return context


# ─── Branch Create View ───────────────────────────────────────────────────────
class BranchCreateView(LoginRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    success_url = reverse_lazy('settings:branch')

    def form_valid(self, form):
        branch = form.save(commit=False)
        branch.modified_user = self.request.user
        branch.save()

        # Assign selected schemes to this branch
        selected = form.cleaned_data.get('schemes', [])
        # Remove branch from schemes not selected
        Scheme.objects.filter(branch=branch).exclude(pk__in=[s.pk for s in selected]).update(branch=None)
        # Assign branch to selected schemes
        Scheme.objects.filter(pk__in=[s.pk for s in selected]).update(branch=branch)
        
        messages.success(self.request, "Branch created and schemes assigned successfully.")
        return redirect(self.success_url)


# ─── Branch Update View ───────────────────────────────────────────────────────
class BranchUpdateView(LoginRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'settings_app/branch_setup.html'
    success_url = reverse_lazy('settings:branch')

    def get_initial(self):
        initial = super().get_initial()
        # Prefill the schemes field
        initial['schemes'] = self.get_object().schemes.all()
        return initial

    def form_valid(self, form):
        branch = form.save(commit=False)
        branch.modified_user = self.request.user
        branch.save()

        selected = form.cleaned_data.get('schemes', [])
        # Remove branch from schemes not selected
        Scheme.objects.filter(branch=branch).exclude(pk__in=[s.pk for s in selected]).update(branch=None)
        # Assign branch to selected schemes
        Scheme.objects.filter(pk__in=[s.pk for s in selected]).update(branch=branch)

        messages.success(self.request, "Branch updated and schemes reassigned successfully.")
        return redirect(self.success_url)


# ─── Branch Delete View ───────────────────────────────────────────────────────
class BranchDeleteView(LoginRequiredMixin, DeleteView):
    model = Branch
    success_url = reverse_lazy('settings:branch')


# ─── Export Branches to CSV ───────────────────────────────────────────────────
@login_required
def export_branches_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="branches.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Code', 'Phone', 'Cell', 'Street', 'Town', 'Province', 'Region', 'Postal Code'])

    for branch in Branch.objects.all():
        writer.writerow([
            branch.name, branch.code, branch.phone, branch.cell,
            branch.street, branch.town, branch.province,
            branch.region, branch.postal_code
        ])

    return response


# ─── Scheme Assignment Logic for Branches ─────────────────────────────────────
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
