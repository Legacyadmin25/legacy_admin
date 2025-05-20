"""
Account Mixins

This module provides mixins for views in the accounts app,
particularly for role-based access control.
"""

from django.contrib.auth.mixins import AccessMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from config.permissions import ROLE_PERMISSIONS, get_primary_group, has_permission

User = get_user_model()

from django.contrib.auth.mixins import UserPassesTestMixin

class GroupRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires the user to be in specific groups and/or have specific permissions.
    If not, they will be redirected to the login page or an appropriate dashboard.
    
    Attributes:
        group_required (list): List of group names required to access the view
        permission_required (str/list): Permission string or list of permission strings required
        owner_field (str): Field name to check for object ownership (for object-level permissions)
    """
    group_required = None  # List of group names required to access the view
    permission_required = None  # Permission string or list of permission strings
    owner_field = None  # Field name to check for object ownership
    raise_exception = True  # Raise PermissionDenied instead of redirecting
    
    def test_func(self):
        """Test if the user has the required permissions."""
        user = self.request.user
        
        # Superusers can access everything
        if user.is_superuser:
            return True
            
        # Check group membership if groups are specified
        if self.group_required:
            user_groups = set(group.name for group in user.groups.all())
            if not any(group in user_groups for group in self.group_required):
                return False
        
        # Check permissions if specified
        if self.permission_required:
            if isinstance(self.permission_required, str):
                perms = [self.permission_required]
            else:
                perms = list(self.permission_required)
                
            if not any(has_permission(user, perm) for perm in perms):
                return False
        
        # Check object ownership if owner_field is specified
        if self.owner_field:
            obj = self.get_object()
            owner = getattr(obj, self.owner_field, None)
            
            # If owner is a callable, call it
            if callable(owner):
                owner = owner()
                
            if owner != user and not user.is_superuser:
                return False
                
        return True
    
    def handle_no_permission(self):
        """Handle unauthorized access."""
        if self.raise_exception or self.request.user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())
            
        return super().handle_no_permission()
    
    def get_permission_denied_message(self):
        """Get the message to display when permission is denied."""
        return _('You do not have permission to access this page.')
    
    def handle_unauthorized_access(self, request):
        """
        Handle unauthorized access by redirecting to an appropriate dashboard
        based on the user's primary group.
        """
        if not request.user.is_authenticated:
            return super().handle_no_permission()
            
        primary_group = get_primary_group(request.user)
        
        # Map of roles to their dashboard URLs
        dashboard_urls = {
            'Internal Admin': 'accounts:superuser_dashboard',
            'Superuser': 'accounts:superuser_dashboard',
            'Administrator': 'accounts:admin_dashboard',
            'BranchOwner': 'accounts:branch_dashboard',
            'SchemeManager': 'accounts:scheme_dashboard',
            'Finance Officer': 'payments:payment_list',
            'Claims Officer': 'claims:claims_home',
            'Agent': 'accounts:agent_dashboard',
            'Compliance Auditor': 'reports:index'
        }
        
        # Get the appropriate dashboard URL or fall back to default
        dashboard = dashboard_urls.get(primary_group, 'dashboard:index')
        
        # Add a message explaining the redirect
        messages.warning(
            request,
            _('You do not have permission to access the requested page. ' \
              'You have been redirected to your dashboard.')
        )
        
        return redirect(reverse(dashboard))

class RoleBasedDashboardMixin:
    """
    Mixin that provides context data and methods for role-based dashboards.
    
    This mixin should be used with views that need to display role-specific
    data and handle role-based access control.
    """
    
    def get_context_data(self, **kwargs):
        """Add role-specific context data to the template."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's primary role and permissions
        primary_role = get_primary_group(user)
        user_permissions = self.get_user_permissions(user)
        
        # Add role-based information to context
        context.update({
            'primary_role': primary_role,
            'user_permissions': user_permissions,
            'available_features': self.get_available_features(user),
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'user_profile': getattr(user, 'profile', None),
        })
        
        # Add role-specific context data
        role_context = self.get_role_specific_context(user, primary_role)
        context.update(role_context)
        
        return context
        
    def get_role_specific_context(self, user, primary_role):
        """
        Get role-specific context data based on the user's primary role.
        
        Args:
            user: The current user
            primary_role (str): The user's primary role
            
        Returns:
            dict: A dictionary of role-specific context data
        """
        context = {}
        
        # Map role names to their corresponding context methods
        role_methods = {
            'Superuser': self.get_superuser_context,
            'Administrator': self.get_administrator_context,
            'BranchOwner': self.get_branch_owner_context,
            'SchemeManager': self.get_scheme_manager_context,
            'Finance Officer': self.get_finance_officer_context,
            'Claims Officer': self.get_claims_officer_context,
            'Agent': self.get_agent_context,
            'Compliance Auditor': self.get_compliance_auditor_context,
        }
        
        # Call the appropriate method if it exists
        if primary_role in role_methods:
            context.update(role_methods[primary_role](user))
            
        return context
    
    def get_user_permissions(self, user):
        """
        Get permissions for a user based on their groups.
        
        Args:
            user: The user to get permissions for
            
        Returns:
            set: A set of permission strings the user has
        """
        if user.is_superuser:
            # Superusers have all permissions
            return set([perm for perms in ROLE_PERMISSIONS.values() for perm in perms])
            
        # Get user's groups
        user_groups = [group.name for group in user.groups.all()]
        
        # Collect permissions from all groups
        permissions = set()
        for group in user_groups:
            if group in ROLE_PERMISSIONS:
                if "all" in ROLE_PERMISSIONS[group]:
                    # If a group has "all" permissions, return all permissions
                    return set([perm for perms in ROLE_PERMISSIONS.values() for perm in perms])
                permissions.update(ROLE_PERMISSIONS[group])
        
        return permissions
    
    def get_available_features(self, user):
        """
        Get a list of features available to the user based on their permissions.
        
        Args:
            user: The user to get features for
            
        Returns:
            set: A set of feature strings the user has access to
        """
        permissions = self.get_user_permissions(user)
        
        # Map permissions to features
        feature_map = {
            # Dashboard features
            'dashboard_access': ['view_dashboard', 'access_overview'],
            
            # User management
            'manage_users': [
                'manage_users', 'view_user_list', 'add_user', 
                'change_user', 'delete_user', 'reset_password'
            ],
            
            # Role and permission management
            'manage_roles': [
                'manage_roles', 'view_role_list', 'add_role', 
                'change_role', 'delete_role', 'assign_roles'
            ],
            
            # Reporting
            'view_reports': [
                'view_reports', 'export_reports', 'schedule_reports',
                'view_audit_logs', 'view_activity_logs'
            ],
            
            # System settings
            'manage_settings': [
                'manage_settings', 'system_settings', 'update_settings',
                'view_system_info', 'manage_integrations'
            ],
            
            # Branch management
            'manage_branches': [
                'view_branch', 'add_branch', 'edit_branch', 
                'delete_branch', 'manage_branch_users'
            ],
            
            # Scheme management
            'manage_schemes': [
                'view_scheme', 'add_scheme', 'edit_scheme',
                'delete_scheme', 'manage_scheme_users'
            ],
            
            # Policy management
            'manage_policies': [
                'view_policy', 'add_policy', 'edit_policy',
                'delete_policy', 'renew_policy', 'cancel_policy'
            ],
            
            # Claims management
            'manage_claims': [
                'view_claim', 'add_claim', 'edit_claim',
                'delete_claim', 'approve_claim', 'reject_claim', 'process_claim'
            ],
            
            # Payment management
            'manage_payments': [
                'view_payment', 'add_payment', 'edit_payment',
                'delete_payment', 'process_payment', 'reconcile_payment'
            ],
            
            # Compliance
            'compliance': [
                'view_compliance', 'manage_compliance', 'run_audit',
                'view_audit_reports', 'export_audit_data'
            ]
        }
        
        # Get all features the user has access to
        available_features = set()
        for permission in permissions:
            if permission in feature_map:
                available_features.update(feature_map[permission])
                
        # Add all features if user has 'all' permission
        if 'all' in permissions:
            available_features.update([f for features in feature_map.values() for f in features])
                
        return available_features
        
    # Role-specific context methods
    
    def get_superuser_context(self, user):
        """Get context data for Superuser role."""
        from django.db.models import Count, Sum, Q
        from datetime import datetime, timedelta
        
        # Get counts for admin dashboard
        from django.contrib.auth import get_user_model
        from schemes.models import Scheme, Branch
        
        User = get_user_model()
        
        # Calculate date ranges
        today = datetime.now().date()
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        # Get user counts
        total_users = User.objects.count()
        new_users_week = User.objects.filter(date_joined__date__gte=last_week).count()
        active_users = User.objects.filter(is_active=True).count()
        
        # Get scheme and branch counts
        total_schemes = Scheme.objects.count()
        total_branches = Branch.objects.count()
        
        # Get recent activities (simplified example)
        recent_activities = [
            {'user': 'System', 'action': 'System update completed', 'timestamp': '2 minutes ago'},
            {'user': 'Admin', 'action': 'Added new scheme', 'timestamp': '1 hour ago'},
            {'user': 'Finance', 'action': 'Processed payments batch', 'timestamp': '3 hours ago'},
        ]
        
        return {
            'total_users': total_users,
            'new_users_week': new_users_week,
            'active_users': active_users,
            'total_schemes': total_schemes,
            'total_branches': total_branches,
            'recent_activities': recent_activities,
            'is_superuser': True,
        }
    
    def get_administrator_context(self, user):
        """Get context data for Administrator role."""
        return {
            'show_admin_controls': True,
            'can_manage_users': True,
            'can_manage_roles': True,
        }
    
    def get_branch_owner_context(self, user):
        """Get context data for Branch Owner role."""
        from schemes.models import Branch
        
        # Get branches this user owns
        branches = user.profile.branches.all() if hasattr(user, 'profile') else Branch.objects.none()
        
        # Get branch statistics
        branch_stats = []
        for branch in branches:
            branch_stats.append({
                'id': branch.id,
                'name': branch.name,
                'scheme_count': branch.schemes.count(),
                'agent_count': branch.agents.count(),
                'policy_count': 0,  # Add actual policy count logic
            })
        
        return {
            'branches': branches,
            'branch_stats': branch_stats,
            'total_branches': branches.count(),
            'can_manage_branches': True,
        }
    
    def get_scheme_manager_context(self, user):
        """Get context data for Scheme Manager role."""
        from schemes.models import Scheme
        
        # Get schemes this user manages
        schemes = user.profile.schemes.all() if hasattr(user, 'profile') else Scheme.objects.none()
        
        # Get scheme statistics
        scheme_stats = []
        for scheme in schemes:
            scheme_stats.append({
                'id': scheme.id,
                'name': scheme.name,
                'policy_count': 0,  # Add actual policy count logic
                'active_agents': scheme.agents.count(),
                'revenue': 0,  # Add actual revenue calculation
            })
        
        return {
            'schemes': schemes,
            'scheme_stats': scheme_stats,
            'total_schemes': schemes.count(),
            'can_manage_schemes': True,
        }
    
    def get_finance_officer_context(self, user):
        """Get context data for Finance Officer role."""
        from datetime import datetime, timedelta
        
        # Example financial data
        today = datetime.now().date()
        last_month = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        
        return {
            'recent_payments': [],  # Add actual recent payments
            'pending_approvals': 0,  # Add actual pending approvals count
            'total_collected': 0,    # Add actual total collected
            'outstanding': 0,        # Add actual outstanding amount
            'start_date': last_month,
            'end_date': today.strftime('%Y-%m-%d'),
        }
    
    def get_claims_officer_context(self, user):
        """Get context data for Claims Officer role."""
        return {
            'pending_claims': 0,     # Add actual pending claims count
            'approved_claims': 0,    # Add actual approved claims count
            'rejected_claims': 0,    # Add actual rejected claims count
            'total_payout': 0,       # Add actual total payout amount
        }
    
    def get_agent_context(self, user):
        """Get context data for Agent role."""
        from datetime import datetime, timedelta
        
        # Example agent data
        today = datetime.now().date()
        last_month = today - timedelta(days=30)
        
        return {
            'policies_sold': 0,      # Add actual policies sold count
            'monthly_target': 0,     # Add actual monthly target
            'conversion_rate': 0,    # Add actual conversion rate
            'commission_earned': 0,  # Add actual commission earned
            'start_date': last_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
        }
    
    def get_compliance_auditor_context(self, user):
        """Get context data for Compliance Auditor role."""
        from datetime import datetime, timedelta
        
        # Example compliance data
        today = datetime.now().date()
        last_month = today - timedelta(days=30)
        
        return {
            'audits_completed': 0,   # Add actual audits completed count
            'compliance_rate': 0,    # Add actual compliance rate
            'pending_reviews': 0,    # Add actual pending reviews count
            'start_date': last_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
        }
