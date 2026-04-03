from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q

from .models_incomplete import IncompleteApplication
from settings_app.models import Agent

class IncompleteApplicationsListView(LoginRequiredMixin, ListView):
    """
    Dashboard view for incomplete applications
    """
    model = IncompleteApplication
    template_name = 'members/diy/incomplete_applications.html'
    context_object_name = 'applications'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter applications based on user role"""
        queryset = IncompleteApplication.objects.filter(status__in=['draft', 'in_progress'])
        
        # Filter by search term if provided
        search_term = self.request.GET.get('search', '')
        if search_term:
            queryset = queryset.filter(
                Q(token__icontains=search_term) | 
                Q(agent__name__icontains=search_term) |
                Q(phone_number__icontains=search_term)
            )
        
        # Filter by status if provided
        status = self.request.GET.get('status', '')
        if status and status in dict(IncompleteApplication.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
            
        # Filter based on user role
        user = self.request.user
        if hasattr(user, 'role'):
            role_type = user.role.role_type
            
            if role_type == 'agent':
                # Agents can only see their own applications
                queryset = queryset.filter(agent=user.agent)
            elif role_type == 'branch_owner':
                # Branch owners can see applications from their branch
                queryset = queryset.filter(branch=user.role.branch)
            elif role_type == 'scheme_manager':
                # Scheme managers can see applications from their scheme
                queryset = queryset.filter(scheme=user.role.scheme)
            # Internal admins can see all applications
        
        return queryset.select_related('agent', 'scheme', 'branch')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['status_choices'] = IncompleteApplication.STATUS_CHOICES
        return context


class IncompleteApplicationDetailView(LoginRequiredMixin, DetailView):
    """
    View details of an incomplete application
    """
    model = IncompleteApplication
    template_name = 'members/diy/incomplete_application_detail.html'
    context_object_name = 'application'
    slug_field = 'token'
    slug_url_kwarg = 'token'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Security check - verify user has permission to view this application
        user = self.request.user
        if hasattr(user, 'role'):
            role_type = user.role.role_type
            
            if role_type == 'agent' and obj.agent != user.agent:
                raise Http404("You don't have permission to view this application")
            elif role_type == 'branch_owner' and obj.branch != user.role.branch:
                raise Http404("You don't have permission to view this application")
            elif role_type == 'scheme_manager' and obj.scheme != user.role.scheme:
                raise Http404("You don't have permission to view this application")
        
        return obj


class ResumeIncompleteApplicationView(View):
    """
    Resume an incomplete application
    """
    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        application = get_object_or_404(IncompleteApplication, token=token)
        
        # Security check - verify user has permission to resume this application
        if request.user.is_authenticated:
            if hasattr(request.user, 'role'):
                role_type = request.user.role.role_type
                
                if role_type == 'agent' and application.agent != request.user.agent:
                    raise Http404("You don't have permission to resume this application")
                elif role_type == 'branch_owner' and application.branch != request.user.role.branch:
                    raise Http404("You don't have permission to resume this application")
                elif role_type == 'scheme_manager' and application.scheme != request.user.role.scheme:
                    raise Http404("You don't have permission to resume this application")
        elif application.session_key and application.session_key != request.session.session_key:
            # For anonymous users, check session key
            raise Http404("You don't have permission to resume this application")
        
        # Store application token in session
        request.session['incomplete_application_token'] = str(application.token)
        
        # Store agent and scheme info in session
        if application.agent:
            request.session['diy_agent_id'] = application.agent.id
        if application.scheme:
            request.session['diy_scheme_id'] = application.scheme.id
        
        # Redirect to the appropriate step
        return redirect('members:diy_application_step', step=application.current_step)


class ResumeApplicationView(View):
    """
    Dedicated page for resuming an incomplete application with a token
    """
    template_name = 'members/diy/resume_application.html'
    
    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        
        try:
            application = get_object_or_404(IncompleteApplication, token=token, status='in_progress')
            
            # Security check - allow access if:
            # 1. User is authenticated and owns the application
            # 2. Session key matches the application's session key
            # 3. Application has no session key (for shared links)
            user_match = request.user.is_authenticated and application.user and application.user == request.user
            session_match = application.session_key and application.session_key == request.session.session_key
            no_session = not application.session_key
            
            if not (user_match or session_match or no_session):
                messages.error(request, "You don't have permission to access this application.")
                return redirect('members:diy_personal_details')
            
            # Store application token in session
            request.session['incomplete_application_token'] = str(application.token)
            
            # Store agent and scheme info in session if available
            if application.agent:
                request.session['diy_agent_id'] = application.agent.id
            if application.scheme:
                request.session['diy_scheme_id'] = application.scheme.id
            
            # Render the resume application template
            context = {
                'application': application,
                'step_labels': {
                    1: 'Personal Details',
                    2: 'Contact Information',
                    3: 'Beneficiaries',
                    4: 'Policy Details',
                    5: 'Payment Options',
                    6: 'Review & Submit',
                    7: 'Success'
                }
            }
            return render(request, self.template_name, context)
            
        except IncompleteApplication.DoesNotExist:
            messages.error(request, "The application you're trying to resume doesn't exist or has expired.")
            return redirect('members:diy_personal_details')


class DeleteIncompleteApplicationView(LoginRequiredMixin, View):
    """
    Delete an incomplete application
    """
    def post(self, request, *args, **kwargs):
        token = kwargs.get('token')
        application = get_object_or_404(IncompleteApplication, token=token)
        
        # Security check - verify user has permission to delete this application
        user = request.user
        if hasattr(user, 'role'):
            role_type = user.role.role_type
            
            if role_type == 'agent' and application.agent != user.agent:
                raise Http404("You don't have permission to delete this application")
            elif role_type == 'branch_owner' and application.branch != user.role.branch:
                raise Http404("You don't have permission to delete this application")
            elif role_type == 'scheme_manager' and application.scheme != user.role.scheme:
                raise Http404("You don't have permission to delete this application")
        
        # Delete the application
        application.delete()
        messages.success(request, "Application deleted successfully")
        
        return HttpResponseRedirect(reverse('members:incomplete_applications'))
