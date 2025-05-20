from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count, Sum, Avg, F, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
import uuid
from datetime import timedelta

from settings_app.models import Branch, Agent, UserRole
from settings_app.mixins import BranchAccessMixin, SchemeAccessMixin, AgentAccessMixin
from schemes.models import Scheme, Policy

# Copy the original file content here and add the regenerate_diy_link function at the end

@require_POST
def regenerate_diy_link(request, agent_id):
    """Regenerate the DIY link for an agent by creating a new token"""
    # Check if user has permission to modify this agent
    user_role = request.user.role.role_type
    agent = get_object_or_404(Agent, id=agent_id)
    
    # Only internal admins, branch owners of the agent's branch, and scheme managers of the agent's scheme can regenerate
    has_permission = False
    
    if user_role == 'internal_admin':
        has_permission = True
    elif user_role == 'branch_owner' and agent.scheme.branch == request.user.role.branch:
        has_permission = True
    elif user_role == 'scheme_manager' and agent.scheme == request.user.role.scheme:
        has_permission = True
    
    if not has_permission:
        messages.error(request, "You don't have permission to regenerate this agent's DIY link.")
        return HttpResponseRedirect(reverse('agent_detail', kwargs={'pk': agent_id}))
    
    # Generate new token
    new_token = str(uuid.uuid4())
    agent.diy_token = new_token
    agent.diy_token_created = timezone.now()
    agent.save()
    
    messages.success(request, f"DIY link for {agent.full_name} has been regenerated successfully.")
    return HttpResponseRedirect(reverse('agent_detail', kwargs={'pk': agent_id}))
