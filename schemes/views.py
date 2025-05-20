from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Q

from schemes.models import Scheme
from schemes.forms import SchemeForm

# ─── Authentication Wrapper ───────────────────────────────────────────
decorators = [login_required]

@method_decorator(login_required, name='dispatch')
class SchemeListView(ListView):
    model = Scheme
    template_name = 'schemes/scheme_list.html'
    context_object_name = 'schemes'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().order_by('-id')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(fsp_number__icontains=q)
            )
        if self.request.user.is_superuser:
            print("[DEBUG] Superuser - schemes count:", qs.count())
            for s in qs:
                print(f"[DEBUG] Scheme: id={s.id}, name={s.name}, branch={s.branch_id}")
        else:
            branch = getattr(self.request.user, 'branchuser', None)
            qs = qs.filter(branch=branch.branch) if branch else Scheme.objects.none()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx
    
@method_decorator(decorators, name='dispatch')
class SchemeCreateView(CreateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('schemes:scheme_list')

    def get_initial(self):
        initial = super().get_initial()
        branch_id = self.request.GET.get('branch')
        if branch_id:
            initial['branch'] = branch_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Scheme created successfully.")
        return super().form_valid(form)

@method_decorator(decorators, name='dispatch')
class SchemeUpdateView(UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('schemes:scheme_list')

    def form_valid(self, form):
        messages.success(self.request, "Scheme updated successfully.")
        return super().form_valid(form)

@method_decorator(decorators, name='dispatch')
class SchemeDeleteView(DeleteView):
    model = Scheme
    template_name = 'settings_app/scheme_confirm_delete.html'
    success_url = reverse_lazy('schemes:scheme_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Scheme deleted.")
        return super().delete(request, *args, **kwargs)
