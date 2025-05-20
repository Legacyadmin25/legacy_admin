from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta
from ..models import Agent

class AgentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'settings_app/agent_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the agent for the current user
        try:
            agent = Agent.objects.get(user=self.request.user)
            context['agent'] = agent
            
            # Add dummy data for the dashboard (replace with actual data)
            context['recent_activity'] = [
                {
                    'title': 'New Policy Created',
                    'description': 'John Doe signed up using your link',
                    'timestamp': timezone.now() - timedelta(hours=2)
                },
                {
                    'title': 'Policy Approved',
                    'description': 'Policy #12345 has been approved',
                    'timestamp': timezone.now() - timedelta(days=1)
                },
                {
                    'title': 'Commission Earned',
                    'description': 'R250.00 commission earned from Policy #12345',
                    'timestamp': timezone.now() - timedelta(days=3)
                },
            ]
            
            # Add agent statistics (replace with actual data)
            context['agent'].referral_count = 12
            context['agent'].active_policies = 8
            context['agent'].commission_earned = 1250.00
            
        except Agent.DoesNotExist:
            context['agent'] = None
            context['recent_activity'] = []
        
        return context
