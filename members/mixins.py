from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone
from .models_incomplete import IncompleteApplication
from settings_app.models import Agent


class AutoSaveViewMixin:
    """
    Mixin to handle auto-saving functionality for multi-step forms
    """
    step_number = None  # Override in subclass
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.incomplete_application = None
        self.load_incomplete_application()
    
    def load_incomplete_application(self):
        """Load incomplete application from session if available"""
        token = self.request.session.get('incomplete_application_token')
        
        if token:
            try:
                self.incomplete_application = IncompleteApplication.objects.get(token=token)
                # Update last activity
                self.incomplete_application.update_activity()
            except IncompleteApplication.DoesNotExist:
                self.incomplete_application = None
    
    def get_form_kwargs(self):
        """Add initial data from incomplete application to form kwargs"""
        kwargs = super().get_form_kwargs()
        
        # If we have an incomplete application with data for this step, use it as initial data
        if self.incomplete_application and self.step_number:
            saved_data = self.incomplete_application.get_step_data(self.step_number)
            if saved_data:
                # If form already has initial data, update it with saved data
                initial = kwargs.get('initial', {})
                initial.update(saved_data)
                kwargs['initial'] = initial
        
        return kwargs
    
    def form_valid(self, form):
        """Save form data to incomplete application when form is valid"""
        response = super().form_valid(form)
        
        # Save form data to incomplete application
        if self.step_number:
            # Get or create incomplete application
            if not self.incomplete_application:
                agent_id = self.request.session.get('diy_agent_id')
                agent = None
                scheme = None
                branch = None
                
                if agent_id:
                    try:
                        agent = Agent.objects.get(pk=agent_id)
                        scheme = agent.scheme
                        branch = agent.scheme.branch if agent.scheme else None
                    except Agent.DoesNotExist:
                        pass
                
                # Create new incomplete application
                self.incomplete_application = IncompleteApplication(
                    agent=agent,
                    scheme=scheme,
                    branch=branch,
                    current_step=self.step_number,
                    session_key=self.request.session.session_key,
                    user=self.request.user if self.request.user.is_authenticated else None
                )
                self.incomplete_application.save()
                
                # Store token in session
                self.request.session['incomplete_application_token'] = str(self.incomplete_application.token)
            
            # Save form data
            form_data = {field: form.cleaned_data.get(field) for field in form.cleaned_data}
            # Convert non-serializable objects to strings
            for key, value in form_data.items():
                if hasattr(value, 'isoformat'):  # Handle date/datetime objects
                    form_data[key] = value.isoformat()
                elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    form_data[key] = str(value)
            
            self.incomplete_application.save_step_data(self.step_number, form_data)
        
        return response


class StepViewMixin:
    """
    Mixin to handle step progression in multi-step forms
    """
    step_number = None  # Override in subclass
    total_steps = None  # Override in subclass
    
    def get_context_data(self, **kwargs):
        """Add step information to context"""
        context = super().get_context_data(**kwargs)
        context['current_step'] = self.step_number
        context['total_steps'] = self.total_steps
        context['steps'] = range(1, self.total_steps + 1)
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Ensure user can't skip steps"""
        # Check if we have an incomplete application
        token = request.session.get('incomplete_application_token')
        if token:
            try:
                incomplete_app = IncompleteApplication.objects.get(token=token)
                # If trying to access a step beyond the current step + 1, redirect to the current step
                if self.step_number > incomplete_app.current_step + 1:
                    return redirect('members:diy_application_step', step=incomplete_app.current_step)
            except IncompleteApplication.DoesNotExist:
                pass
        
        return super().dispatch(request, *args, **kwargs)
