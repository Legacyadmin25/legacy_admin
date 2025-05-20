from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class RoleRequiredMixin(AccessMixin):
    """
    Mixin to enforce role-based access control.
    Requires the user to have a specific role to access the view.
    """
    allowed_roles = []  # List of role types that can access the view
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if the user has a role
        try:
            user_role = request.user.role
        except:
            messages.error(request, "You don't have the required permissions to access this page.")
            return redirect('dashboard')
        
        # Check if the user's role is allowed
        if self.allowed_roles and user_role.role_type not in self.allowed_roles:
            messages.error(request, "You don't have the required permissions to access this page.")
            return redirect('dashboard')
        
        # For scheme_manager, check if they're accessing their own scheme
        if user_role.role_type == 'scheme_manager' and 'scheme_id' in kwargs:
            if user_role.scheme and str(user_role.scheme.id) != kwargs['scheme_id']:
                messages.error(request, "You can only access your own scheme.")
                return redirect('scheme_dashboard', scheme_id=user_role.scheme.id)
        
        # For branch_owner, check if they're accessing their own branch
        if user_role.role_type == 'branch_owner' and 'branch_id' in kwargs:
            if user_role.branch and str(user_role.branch.id) != kwargs['branch_id']:
                messages.error(request, "You can only access your own branch.")
                return redirect('branch_dashboard', branch_id=user_role.branch.id)
        
        return super().dispatch(request, *args, **kwargs)


class BranchAccessMixin(RoleRequiredMixin):
    """Mixin for views that require branch access"""
    allowed_roles = ['internal_admin', 'branch_owner', 'compliance_auditor']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_read_only'] = self.request.user.role.role_type == 'compliance_auditor'
        return context


class SchemeAccessMixin(RoleRequiredMixin):
    """Mixin for views that require scheme access"""
    allowed_roles = ['internal_admin', 'branch_owner', 'scheme_manager', 'compliance_auditor']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_read_only'] = self.request.user.role.role_type == 'compliance_auditor'
        
        # Branch owners can only view, not edit schemes
        if self.request.user.role.role_type == 'branch_owner':
            context['is_read_only'] = True
            
        return context


class AgentAccessMixin(RoleRequiredMixin):
    """Mixin for views that require agent access"""
    allowed_roles = ['internal_admin', 'branch_owner', 'scheme_manager', 'compliance_auditor']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_read_only'] = self.request.user.role.role_type in ['compliance_auditor', 'branch_owner', 'scheme_manager']
        return context
