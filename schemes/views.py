from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from schemes.models import Scheme
from schemes.forms import SchemeForm
from config.permissions import can_view_scheme, get_user_accessible_schemes

# ─── Authentication Wrapper ───────────────────────────────────────────
decorators = [login_required]

@method_decorator(login_required, name='dispatch')
class SchemeListView(ListView):
    model = Scheme
    template_name = 'schemes/scheme_list.html'
    context_object_name = 'schemes'
    paginate_by = 10

    def get_queryset(self):
        # Get all accessible schemes for this user
        qs = get_user_accessible_schemes(self.request.user)
        
        # Apply search filter
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(fsp_number__icontains=q) |
                Q(prefix__icontains=q) |
                Q(registration_no__icontains=q)
            )
        
        return qs.order_by('-id')

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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            # Create a mutable copy of the POST data
            data = self.request.POST.copy()
            # If bank is selected, update branch_code from the selected bank
            if 'bank' in data and data['bank']:
                from branches.models import Bank
                try:
                    bank = Bank.objects.get(pk=data['bank'])
                    data['branch_code'] = bank.branch_code
                except (Bank.DoesNotExist, ValueError):
                    pass
            kwargs['data'] = data
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not self.request.user.is_superuser:
            # Pre-fill with user's assigned branch
            if self.request.user.branch:
                initial['branch'] = self.request.user.branch
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add bank options to the context
        from branches.models import Bank
        context['bank_options'] = [
            {
                'id': bank.id,
                'name': bank.name,
                'branch_code': bank.branch_code
            } for bank in Bank.objects.all().order_by('name')
        ]
        return context

    def form_valid(self, form):
        # Explicitly save the active status
        self.object = form.save(commit=False)
        self.object.active = 'active' in form.data  # Check if active was in the form data
        self.object.save()
        form.save_m2m()  # Save many-to-many data if any
        messages.success(self.request, "Scheme created successfully.")
        return super().form_valid(form)

@method_decorator(decorators, name='dispatch')
class SchemeUpdateView(UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('schemes:scheme_list')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Check if user can view this scheme
        if not can_view_scheme(self.request.user, obj):
            raise PermissionDenied("You do not have permission to edit this scheme.")
        return obj
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            # Create a mutable copy of the POST data
            data = self.request.POST.copy()
            # If bank is selected, update branch_code from the selected bank
            if 'bank' in data and data['bank']:
                from branches.models import Bank
                try:
                    bank = Bank.objects.get(pk=data['bank'])
                    data['branch_code'] = bank.branch_code
                except (Bank.DoesNotExist, ValueError):
                    pass
            # Ensure active status is included in the form data
            data['active'] = data.get('active', 'off')
            kwargs['data'] = data
        return kwargs
        
    def form_valid(self, form):
        # Explicitly save the active status
        self.object = form.save(commit=False)
        self.object.active = 'active' in form.data  # Check if active was in the form data
        self.object.save()
        form.save_m2m()  # Save many-to-many data if any
        messages.success(self.request, "Scheme updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add bank options to the context
        from branches.models import Bank
        context['bank_options'] = [
            {
                'id': bank.id,
                'name': bank.name,
                'branch_code': bank.branch_code
            } for bank in Bank.objects.all().order_by('name')
        ]
        # Set the initial branch code if bank is selected
        if self.object and self.object.bank:
            context['form'].fields['branch_code'].initial = self.object.bank.branch_code
        return context

    def form_valid(self, form):
        # Update branch code if bank is changed
        if 'bank' in form.changed_data and form.cleaned_data.get('bank'):
            form.instance.branch_code = form.cleaned_data['bank'].branch_code
        messages.success(self.request, 'Scheme updated successfully.')
        return super().form_valid(form)

@method_decorator(decorators, name='dispatch')
class SchemeDeleteView(DeleteView):
    model = Scheme
    template_name = 'settings_app/scheme_confirm_delete.html'
    success_url = reverse_lazy('schemes:scheme_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Check if user can view this scheme
        if not can_view_scheme(self.request.user, obj):
            raise PermissionDenied("You do not have permission to delete this scheme.")
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Scheme deleted.")
        return super().delete(request, *args, **kwargs)
