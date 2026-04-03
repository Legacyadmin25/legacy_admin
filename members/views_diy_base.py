from django.views.generic import FormView, TemplateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.http import Http404

from settings_app.models import Agent
from .models_incomplete import IncompleteApplication
from .mixins import AutoSaveViewMixin, StepViewMixin

class DIYBaseView(AutoSaveViewMixin, StepViewMixin, FormView):
    """
    Base view for DIY application steps with auto-save functionality
    """
    template_name = 'members/diy/base_application_autosave.html'
    success_url = None
    form_class = None
    step_number = None
    total_steps = 7  # Default, can be overridden in subclasses
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has access to this step and load agent/scheme data"""
        # Check if we have agent info in session
        self.agent = None
        self.scheme = None
        
        agent_id = request.session.get('diy_agent_id')
        if agent_id:
            try:
                self.agent = Agent.objects.get(pk=agent_id)
                self.scheme = self.agent.scheme
            except Agent.DoesNotExist:
                pass
        
        # If no agent found and not resuming an application, redirect to start
        if not self.agent and not request.session.get('incomplete_application_token'):
            messages.error(request, "Your session has expired. Please start again.")
            return redirect('members:diy_start')
        
        # Check if user is trying to skip ahead
        token = request.session.get('incomplete_application_token')
        if token and self.step_number > 1:
            try:
                incomplete_app = IncompleteApplication.objects.get(token=token)
                # If trying to access a step beyond the current step + 1, redirect to the current step
                if self.step_number > incomplete_app.current_step + 1:
                    messages.warning(request, "Please complete the previous steps first.")
                    return redirect('members:diy_application_step', step=incomplete_app.current_step)
            except IncompleteApplication.DoesNotExist:
                # If no incomplete application found but trying to access a step beyond 1, redirect to step 1
                if self.step_number > 1:
                    messages.warning(request, "Please start from the beginning.")
                    return redirect('members:diy_application_step', step=1)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add common context data for all steps"""
        context = super().get_context_data(**kwargs)
        
        # Add agent and scheme info
        context['agent'] = self.agent
        context['scheme'] = self.scheme
        
        # Add step navigation info
        context['prev_step_url'] = self.get_prev_step_url()
        context['is_final_step'] = (self.step_number == self.total_steps)
        
        # Add step labels
        context['step_labels'] = self.get_step_labels()
        
        return context
    
    def get_prev_step_url(self):
        """Get URL for the previous step"""
        if self.step_number > 1:
            return reverse('members:diy_application_step', kwargs={'step': self.step_number - 1})
        return None
    
    def get_success_url(self):
        """Get URL for the next step or completion page"""
        if self.step_number < self.total_steps:
            return reverse('members:diy_application_step', kwargs={'step': self.step_number + 1})
        
        # If this is the final step, redirect to completion page
        # We'll need the application token for this
        token = self.request.session.get('incomplete_application_token')
        if token:
            return reverse('members:diy_completion', kwargs={'token': token})
        
        # Fallback to start page if something went wrong
        return reverse('members:diy_start')
    
    def get_step_labels(self):
        """Get labels for each step"""
        return {
            1: 'Personal Details',
            2: 'Contact Info',
            3: 'Beneficiaries',
            4: 'Policy Details',
            5: 'Payment Options',
            6: 'Review',
            7: 'Confirmation'
        }
    
    def form_valid(self, form):
        """Process form data when valid"""
        # Save form data to the model
        self.process_form_data(form)
        
        # Mark the step as completed in the incomplete application
        if self.incomplete_application:
            self.incomplete_application.current_step = self.step_number + 1
            self.incomplete_application.save(update_fields=['current_step', 'updated_at'])
        
        return super().form_valid(form)
    
    def process_form_data(self, form):
        """
        Process form data - to be implemented by subclasses
        This method should handle saving the form data to the appropriate models
        """
        pass


class DIYCompletionView(TemplateView):
    """
    View for the completion page after all steps are completed
    """
    template_name = 'members/diy/completion.html'
    
    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        
        try:
            # Get the incomplete application
            incomplete_app = IncompleteApplication.objects.get(token=token)
            
            # Mark it as completed
            incomplete_app.mark_completed()
            
            # Clear session data
            request.session.pop('incomplete_application_token', None)
            
            # Add application data to context
            self.application = incomplete_app
            
        except IncompleteApplication.DoesNotExist:
            raise Http404("Application not found")
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application'] = self.application
        return context
