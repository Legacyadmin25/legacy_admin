"""
Views for the accounts application.

This module contains all the views for user authentication, profile management,
and role-based access control in the accounts app.
"""
import json
from typing import Any, Dict, List, Optional, Union

from django.contrib import messages
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
    PermissionRequiredMixin,
)
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, QuerySet
from django.forms import Form, ModelForm
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    Http404,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin

from braces.views import (
    FormMessagesMixin,
    JSONResponseMixin,
    LoginRequiredMixin as BracesLoginRequiredMixin,
    PermissionRequiredMixin as BracesPermissionRequiredMixin,
    StaffuserRequiredMixin,
    SuperuserRequiredMixin,
)

from config.permissions import (
    get_primary_group,
    get_user_permissions,
    ROLE_PERMISSIONS,
    has_permission,
)
from .forms import (
    UserRegistrationForm,
    ProfileUpdateForm,
    EmailChangeForm,
    UserCreateForm,
    UserUpdateForm,
    RoleForm,
    PasswordChangeForm,
    AdminPasswordChangeForm,
)
from .mixins import (
    GroupRequiredMixin,
    RoleBasedDashboardMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django import forms
from .models import Profile
from django.contrib.auth.models import Group


# Get the custom user model
User = get_user_model()

# Constants
DEFAULT_REDIRECT_URL = reverse_lazy('accounts:profile')
LOGIN_URL = reverse_lazy('accounts:login')

class RoleBasedLoginView(LoginView):
    """
    Custom login view that redirects users to their appropriate dashboard
    based on their role after successful authentication.
    """
    template_name = 'accounts/auth/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """
        Determine the URL to redirect to after successful login.
        
        Returns:
            str: The URL to redirect to after login
        """
        user = self.request.user
        
        # Get the 'next' parameter from the request
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
            
        # Check if user is a superuser
        if user.is_superuser:
            return reverse('accounts:superuser_dashboard')
            
        # Get user's primary group based on role hierarchy
        primary_group = get_primary_group(user)
        
        # Redirect based on primary group
        if primary_group == 'Internal Admin':
            return reverse('accounts:superuser_dashboard')
        elif primary_group == 'Administrator':
            return reverse('accounts:admin_dashboard')
        elif primary_group == 'BranchOwner':
            return reverse('accounts:branch_dashboard')
        elif primary_group == 'SchemeManager':
            return reverse('accounts:scheme_dashboard')
        elif primary_group == 'Finance Officer':
            return reverse('accounts:finance_dashboard')
        elif primary_group == 'Claims Officer':
            return reverse('accounts:claims_dashboard')
        elif primary_group == 'Agent':
            return reverse('accounts:agent_dashboard')
        elif primary_group == 'Compliance Auditor':
            return reverse('accounts:compliance_dashboard')
        
        # Default fallback
        return reverse('accounts:profile')
    
    def form_valid(self, form):
        """
        Log the user in and set session data.
        """
        # Call the parent's form_valid method to log the user in
        response = super().form_valid(form)
        
        # Update the user's last login time
        user = form.get_user()
        user.profile.update_last_login()
        
        # Add a welcome message
        messages.success(
            self.request,
            f'Welcome back, {user.get_full_name() or user.username}!',
            extra_tags='alert-success'
        )
        
        return response


class UserRegistrationView(FormView):
    """
    View for user registration.
    """
    template_name = 'accounts/auth/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('accounts:registration_complete')
    
    def dispatch(self, request, *args, **kwargs):
        """
        Redirect to the home page if user is already authenticated.
        """
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        # Create the user
        user = form.save(commit=False)
        user.is_active = False  # User needs to verify email first
        user.save()
        
        # Create the user's profile
        profile = user.profile
        profile.phone = form.cleaned_data.get('phone', '')
        profile.save()
        
        # Send verification email
        # Add success message
        messages.success(
            self.request,
            'Registration successful! Please check your email to verify your account.',
            extra_tags='alert-success'
        )
        
        return super().form_valid(form)


class EmailVerificationView(View):
    """
    View for email verification.
    """
    def get(self, request, uidb64, token):
        """
        Verify the user's email address.
        """
        try:
            # Verify the token and activate the user
            user = User.verify_email_token(uidb64, token)
            if user is not None:
                user.is_active = True
                user.save()
                
                # Log the user in
                login(request, user)
                
                # Add success message
                messages.success(
                    request,
                    'Your email has been verified and your account is now active!',
                    extra_tags='alert-success'
                )
                
                return redirect('accounts:profile')
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            pass
        
        # If we get here, the token was invalid
        messages.error(
            request,
            'The verification link is invalid or has expired.',
            extra_tags='alert-danger'
        )
        return redirect('accounts:login')

# Profile Views
class ProfileView(LoginRequiredMixin, DetailView):
    """
    View for displaying a user's profile.
    """
    model = User
    template_name = 'accounts/profile/detail.html'
    context_object_name = 'profile_user'
    
    def get_object(self, queryset=None):
        """
        Return the user whose profile is being viewed.
        """
        if 'pk' in self.kwargs:
            return get_object_or_404(User, pk=self.kwargs['pk'])
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data.
        """
        context = super().get_context_data(**kwargs)
        context['is_own_profile'] = (self.object == self.request.user)
        return context


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    View for updating a user's profile.
    """
    model = Profile
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile/update.html'
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Your profile has been updated successfully.'
    
    def get_object(self, queryset=None):
        """
        Return the profile to be updated.
        """
        return self.request.user.profile
    
    def get_form_kwargs(self):
        """
        Add the request to the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class EmailChangeView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """
    View for changing a user's email address.
    """
    template_name = 'accounts/profile/email_change.html'
    form_class = EmailChangeForm
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Your email address has been updated successfully.'
    
    def get_form_kwargs(self):
        """
        Add the user to the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        old_email = self.request.user.email
        new_email = form.cleaned_data['new_email']
        
        # Update the user's email
        user = self.request.user
        user.email = new_email
        user.save(update_fields=['email'])
        
        return super().form_valid(form)


class CustomPasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    """
    View for changing a user's password.
    """
    template_name = 'accounts/profile/password_change.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('accounts:password_change_done')
    success_message = 'Your password has been changed successfully.'
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        response = super().form_valid(form)
        
        # Update the session with the new password hash
        update_session_auth_hash(self.request, form.user)
        
        # Add success message
        messages.success(
            self.request,
            'Your password has been changed successfully.',
            extra_tags='alert-success'
        )
        
        return response


class AccountDeleteView(LoginRequiredMixin, FormView):
    """
    View for deleting a user's account.
    """
    template_name = 'accounts/profile/delete.html'
    form_class = forms.Form  # Simple confirmation form
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        user = self.request.user
        
        # Log the user out
        logout(self.request)
        
        # Delete the user
        user.delete()
        
        # Add success message
        messages.success(
            self.request,
            'Your account has been deleted successfully. We\'re sorry to see you go!',
            extra_tags='alert-success'
        )
        
        return super().form_valid(form)


# User Management Views
class UserListView(LoginRequiredMixin, StaffuserRequiredMixin, ListView):
    """
    View for listing all users in the system.
    """
    model = User
    template_name = 'accounts/users/list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Return the list of users, excluding superusers unless the current user is a superuser.
        """
        queryset = User.objects.all().select_related('profile')
        
        # If not a superuser, exclude superusers from the list
        if not self.request.user.is_superuser:
            queryset = queryset.filter(is_superuser=False)
            
        # Apply search filter if provided
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            
        return queryset.order_by('-date_joined')


class UserCreateView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, CreateView):
    """
    View for creating a new user.
    """
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/users/create.html'
    success_url = reverse_lazy('accounts:user_list')
    success_message = 'User created successfully.'
    
    def get_form_kwargs(self):
        """
        Add the request to the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        # Save the user
        self.object = form.save(commit=False)
        
        # Set the password if provided
        if form.cleaned_data.get('password1'):
            self.object.set_password(form.cleaned_data['password1'])
        
        # Save the user
        self.object.save()
        
        # Save the user's profile
        profile = self.object.profile
        profile.phone = form.cleaned_data.get('phone', '')
        profile.save()
        
        # Add groups
        if form.cleaned_data.get('groups'):
            self.object.groups.set(form.cleaned_data['groups'])
        
        # Add success message
        messages.success(
            self.request,
            f'User {self.object.get_full_name() or self.object.username} created successfully.',
            extra_tags='alert-success'
        )
        
        return super().form_valid(form)


class UserDetailView(LoginRequiredMixin, StaffuserRequiredMixin, DetailView):
    """
    View for displaying a user's details.
    """
    model = User
    template_name = 'accounts/users/detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data.
        """
        context = super().get_context_data(**kwargs)
        context['is_own_profile'] = (self.object == self.request.user)
        return context


class UserUpdateView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    View for updating a user's details.
    """
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/users/update.html'
    context_object_name = 'user_obj'
    success_message = 'User updated successfully.'
    
    def get_success_url(self):
        """
        Return the URL to redirect to after successful update.
        """
        return reverse('accounts:user_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        """
        Add the request to the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        # Save the user
        self.object = form.save(commit=False)
        
        # Update the password if provided
        if form.cleaned_data.get('password1'):
            self.object.set_password(form.cleaned_data['password1'])
        
        # Save the user
        self.object.save()
        
        # Save the user's profile
        profile = self.object.profile
        profile.phone = form.cleaned_data.get('phone', '')
        profile.save()
        
        # Update groups
        if 'groups' in form.cleaned_data:
            self.object.groups.set(form.cleaned_data['groups'])
        
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    View for deleting a user.
    """
    model = User
    template_name = 'accounts/users/delete.html'
    success_url = reverse_lazy('accounts:user_list')
    success_message = 'User deleted successfully.'
    context_object_name = 'user_obj'
    
    def delete(self, request, *args, **kwargs):
        """
        Call the delete() method on the fetched object and then redirect to the
        success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Don't allow users to delete themselves
        if self.object == request.user:
            messages.error(
                request,
                'You cannot delete your own account while logged in.',
                extra_tags='alert-danger'
            )
            return redirect('accounts:user_list')
        
        # Delete the user
        self.object.delete()
        
        # Add success message
        messages.success(
            request,
            self.success_message,
            extra_tags='alert-success'
        )
        
        return HttpResponseRedirect(success_url)


class AdminPasswordChangeView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, FormView):
    """
    View for an admin to change a user's password.
    """
    template_name = 'accounts/users/change_password.html'
    form_class = AdminPasswordChangeForm
    success_message = 'Password changed successfully.'
    
    def get_form_kwargs(self):
        """
        Add the user to the form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.get_user()
        return kwargs
    
    def get_success_url(self):
        """
        Return the URL to redirect to after successful password change.
        """
        return reverse('accounts:user_detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_user(self):
        """
        Return the user whose password is being changed.
        """
        return get_object_or_404(User, pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        """
        Add the user to the context.
        """
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.get_user()
        return context
    
    def form_valid(self, form):
        """
        Process the form after it has been validated.
        """
        user = self.get_user()
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        
        # Add success message
        messages.success(
            self.request,
            f'Password for {user.get_full_name() or user.username} has been changed successfully.',
            extra_tags='alert-success'
        )
        
        return super().form_valid(form)


# Role Management Views
class RoleListView(LoginRequiredMixin, StaffuserRequiredMixin, ListView):
    """
    View for listing all roles in the system.
    """
    model = Group
    template_name = 'accounts/roles/list.html'
    context_object_name = 'roles'
    
    def get_queryset(self):
        """
        Return the list of roles, ordered by name.
        """
        return Group.objects.all().order_by('name')


class RoleDetailView(LoginRequiredMixin, StaffuserRequiredMixin, DetailView):
    """
    View for displaying a role's details.
    """
    model = Group
    template_name = 'accounts/roles/detail.html'
    context_object_name = 'role'
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data.
        """
        context = super().get_context_data(**kwargs)
        context['users'] = self.object.user_set.all().select_related('profile')
        context['permissions'] = self.object.permissions.all()
        return context


class RoleCreateView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, CreateView):
    """
    View for creating a new role.
    """
    model = Group
    form_class = RoleForm
    template_name = 'accounts/roles/create.html'
    success_url = reverse_lazy('accounts:role_list')
    success_message = 'Role created successfully.'


class RoleUpdateView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    View for updating a role.
    """
    model = Group
    form_class = RoleForm
    template_name = 'accounts/roles/update.html'
    success_url = reverse_lazy('accounts:role_list')
    success_message = 'Role updated successfully.'
    context_object_name = 'role'


class RoleDeleteView(LoginRequiredMixin, StaffuserRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    View for deleting a role.
    """
    model = Group
    template_name = 'accounts/roles/delete.html'
    success_url = reverse_lazy('accounts:role_list')
    success_message = 'Role deleted successfully.'
    context_object_name = 'role'
    
    def delete(self, request, *args, **kwargs):
        """
        Call the delete() method on the fetched object and then redirect to the
        success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Check if the role has users assigned to it
        if self.object.user_set.exists():
            messages.error(
                request,
                'Cannot delete a role that has users assigned to it. '
                'Please reassign or delete the users first.',
                extra_tags='alert-danger'
            )
            return redirect('accounts:role_detail', pk=self.object.pk)
        
        # Delete the role
        self.object.delete()
        
        # Add success message
        messages.success(
            request,
            self.success_message,
            extra_tags='alert-success'
        )
        
        return HttpResponseRedirect(success_url)


# API Views
class UserAutocompleteView(LoginRequiredMixin, JSONResponseMixin, View):
    """
    View for autocompleting user search.
    """
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests.
        """
        query = request.GET.get('q', '').strip()
        
        if not query or len(query) < 2:
            return self.render_json_response({'results': []})
        
        # Search for users by username, email, first name, or last name
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).select_related('profile')[:10]
        
        # Format the results for Select2
        results = [{
            'id': user.id,
            'text': f'{user.get_full_name()} ({user.username})',
            'username': user.username,
            'email': user.email,
            'avatar_url': user.profile.get_avatar_url() if hasattr(user, 'profile') else ''
        } for user in users]
        
        return self.render_json_response({'results': results})


@require_http_methods(['GET'])
@login_required
def check_username_availability(request):
    """
    Check if a username is available.
    """
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'valid': False, 'message': 'Username is required'})
    
    # Check if the username is already taken
    exists = User.objects.filter(username__iexact=username).exists()
    
    return JsonResponse({
        'valid': not exists,
        'message': 'This username is already taken' if exists else 'Username is available'
    })


@require_http_methods(['GET'])
@login_required
def check_email_availability(request):
    """
    Check if an email is available.
    """
    email = request.GET.get('email', '').strip()
    
    if not email:
        return JsonResponse({'valid': False, 'message': 'Email is required'})
    
    # Check if the email is already taken
    exists = User.objects.filter(email__iexact=email).exists()
    
    return JsonResponse({
        'valid': not exists,
        'message': 'This email is already registered' if exists else 'Email is available'
    })


# Dashboard Views
class RoleBasedDashboard(LoginRequiredMixin, RoleBasedDashboardMixin, GroupRequiredMixin, TemplateView):
    """
    Base class for all role-based dashboards.
    """
    group_name = None
    
    def get_template_names(self):
        """
        Return the template name based on the user's role.
        """
        if self.group_name == 'Internal Admin':
            return ['accounts/dashboards/superuser.html']
        elif self.group_name == 'Administrator':
            return ['accounts/dashboards/admin.html']
        elif self.group_name == 'BranchOwner':
            return ['accounts/dashboards/branch.html']
        elif self.group_name == 'SchemeManager':
            return ['accounts/dashboards/scheme.html']
        elif self.group_name == 'Agent':
            return ['accounts/dashboards/agent.html']
        elif self.group_name == 'Finance Officer':
            return ['accounts/dashboards/finance.html']
        elif self.group_name == 'Claims Officer':
            return ['accounts/dashboards/claims.html']
        elif self.group_name == 'Compliance Auditor':
            return ['accounts/dashboards/compliance.html']
        else:
            return ['accounts/dashboards/default.html']
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add role-specific data
        if self.group_name == 'BranchOwner':
            # Add branch-specific data
            context['branches'] = user.branches.all() if hasattr(user, 'branches') else []
            context['total_schemes'] = sum(branch.schemes.count() for branch in context['branches']) if context['branches'] else 0
            context['total_policies'] = self.get_branch_policies_count(user)
            
        elif self.group_name == 'SchemeManager':
            # Add scheme-specific data
            context['schemes'] = user.schemes.all() if hasattr(user, 'schemes') else []
            context['total_policies'] = self.get_scheme_policies_count(user)
            context['total_agents'] = self.get_scheme_agents_count(user)
            
        elif self.group_name == 'Agent':
            # Add agent-specific data
            context['total_policies'] = self.get_agent_policies_count(user)
            context['recent_policies'] = self.get_agent_recent_policies(user)
            
        return context
        
    def get_branch_policies_count(self, user):
        # This would be implemented based on your data model
        return 0
        
    def get_scheme_policies_count(self, user):
        # This would be implemented based on your data model
        return 0
        
    def get_scheme_agents_count(self, user):
        # This would be implemented based on your data model
        return 0
        
    def get_agent_policies_count(self, user):
        # This would be implemented based on your data model
        return 0
        
    def get_agent_recent_policies(self, user):
        # This would be implemented based on your data model
        return []

class SuperuserDashboard(LoginRequiredMixin, RoleBasedDashboardMixin, TemplateView):
    template_name = "accounts/superuser_dashboard.html"
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to access the superuser dashboard.")
            return redirect('dashboard:index')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add superuser-specific data
        context['total_users'] = User.objects.count()
        context['total_groups'] = Group.objects.count()
        context['role_permissions'] = ROLE_PERMISSIONS
        
        # System health metrics could be added here
        context['system_health'] = {
            'database_status': 'Healthy',
            'cache_status': 'Healthy',
            'storage_status': 'Healthy',
            'api_status': 'Healthy',
        }
        
        return context

class AdminDashboard(RoleBasedDashboard):
    template_name = "accounts/admin_dashboard.html"
    group_name = "Administrator"

class BranchDashboard(RoleBasedDashboard):
    template_name = "accounts/branch_dashboard.html"
    group_name = "BranchOwner"

class SchemeDashboard(RoleBasedDashboard):
    template_name = "accounts/scheme_dashboard.html"
    group_name = "SchemeManager"

class FinanceDashboard(RoleBasedDashboard):
    template_name = "accounts/finance_dashboard.html"
    group_name = "Finance Officer"

class ClaimsDashboard(RoleBasedDashboard):
    template_name = "accounts/claims_dashboard.html"
    group_name = "Claims Officer"

class ComplianceDashboard(RoleBasedDashboard):
    template_name = "accounts/compliance_dashboard.html"
    group_name = "Compliance Auditor"
    
# Home View
from django.views.generic import TemplateView
class HomeView(TemplateView):
    template_name = "accounts/home.html"

# Account Settings View
class AccountSettingsView(TemplateView):
    template_name = "accounts/account_settings.html"

# Agent Dashboard
class AgentDashboard(RoleBasedDashboard):
    template_name = "accounts/agent_dashboard.html"
    group_name = "Agent"

# Profile Update
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ['email', 'first_name', 'last_name']
    template_name = 'accounts/profile_update.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('accounts:profile_update')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['primary_role'] = get_primary_group(self.request.user)
        context['user_permissions'] = get_user_permissions(self.request.user)
        return context

# Password Change
class PasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')
