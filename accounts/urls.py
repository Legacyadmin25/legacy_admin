"""
URL configuration for the accounts app.

This module defines the URL patterns for the accounts application,
including authentication, user management, and profile-related views.
"""
from django.urls import path, include, reverse_lazy
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.views.generic import TemplateView

from . import views

app_name = "accounts"

# Authentication URL patterns
auth_patterns = [
    path("login/", views.RoleBasedLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("accounts:login")), name="logout"),
    path("register/", views.UserRegistrationView.as_view(), name="register"),
    path("verify-email/<str:uidb64>/<str:token>/", 
         views.EmailVerificationView.as_view(), 
         name="verify_email"),
    path("password-reset/", 
         PasswordResetView.as_view(
             template_name="accounts/auth/password_reset.html",
             email_template_name="accounts/emails/password_reset_email.html",
             subject_template_name="accounts/emails/password_reset_subject.txt",
             success_url=reverse_lazy("accounts:password_reset_done")
         ), 
         name="password_reset"),
    path("password-reset/done/", 
         PasswordResetDoneView.as_view(
             template_name="accounts/auth/password_reset_done.html"
         ), 
         name="password_reset_done"),
    path("password-reset/confirm/<uidb64>/<token>/", 
         PasswordResetConfirmView.as_view(
             template_name="accounts/auth/password_reset_confirm.html",
             success_url=reverse_lazy("accounts:password_reset_complete")
         ), 
         name="password_reset_confirm"),
    path("password-reset/complete/", 
         PasswordResetCompleteView.as_view(
             template_name="accounts/auth/password_reset_complete.html"
         ), 
         name="password_reset_complete"),
]

# Dashboard URL patterns
dashboard_patterns = [
    path("superuser/", views.SuperuserDashboard.as_view(), name="superuser_dashboard"),
    path("admin/", views.AdminDashboard.as_view(), name="admin_dashboard"),
    path("branch/", views.BranchDashboard.as_view(), name="branch_dashboard"),
    path("scheme/", views.SchemeDashboard.as_view(), name="scheme_dashboard"),
    path("finance/", views.FinanceDashboard.as_view(), name="finance_dashboard"),
    path("claims/", views.ClaimsDashboard.as_view(), name="claims_dashboard"),
    path("agent/", views.AgentDashboard.as_view(), name="agent_dashboard"),
    path("compliance/", views.ComplianceDashboard.as_view(), name="compliance_dashboard"),
]

# Profile and account management URL patterns
account_patterns = [
    path("profile/", views.ProfileUpdateView.as_view(), name="profile_update"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("email/change/", views.EmailChangeView.as_view(), name="email_change"),
    path("delete-account/", views.AccountDeleteView.as_view(), name="account_delete"),
    path("settings/", views.AccountSettingsView.as_view(), name="account_settings"),
]

# User management URL patterns (admin only)
user_management_patterns = [
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/update/", views.UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
    path("users/<int:pk>/change-password/", 
         views.AdminPasswordChangeView.as_view(), 
         name="admin_password_change"),
]

# Role and permission management URL patterns (admin only)
role_management_patterns = [
    path("roles/", views.RoleListView.as_view(), name="role_list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/", views.RoleDetailView.as_view(), name="role_detail"),
    path("roles/<int:pk>/update/", views.RoleUpdateView.as_view(), name="role_update"),
    path("roles/<int:pk>/delete/", views.RoleDeleteView.as_view(), name="role_delete"),
]

# API endpoints for AJAX requests
api_patterns = [
    path("check-username/", views.check_username_availability, name="check_username"),
    path("check-email/", views.check_email_availability, name="check_email"),
    path("user-autocomplete/", views.UserAutocompleteView.as_view(), name="user_autocomplete"),
]

# Main URL patterns
urlpatterns = [
    # Authentication
    path("auth/", include((auth_patterns, 'auth'))),
    
    # Dashboards
    path("dashboard/", include((dashboard_patterns, 'dashboard'))),
    
    # Account management
    path("account/", include((account_patterns, 'account'))),
    
    # User management (admin only)
    path("users/", include((user_management_patterns, 'users'))),
    
    # Role management (admin only)
    path("roles/", include((role_management_patterns, 'roles'))),
    
    # API endpoints
    path("api/", include((api_patterns, 'api'))),
    
    # Home/landing page
    path("", views.HomeView.as_view(), name="home"),
]
