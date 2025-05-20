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
from schemes.models import Scheme, Plan
from members.models import Member, Policy
from payments.models import Payment

class BranchDashboardView(LoginRequiredMixin, BranchAccessMixin, DetailView):
    """Dashboard view for a branch showing all schemes and performance metrics"""
    model = Branch
    template_name = 'settings_app/dashboards/branch_dashboard.html'
    context_object_name = 'branch'
    pk_url_kwarg = 'pk'
    
    def get_object(self, queryset=None):
        # For internal_admin and compliance_auditor, get the branch by ID
        if self.request.user.role.role_type in ['internal_admin', 'compliance_auditor']:
            return get_object_or_404(Branch, pk=self.kwargs.get('pk'))
        
        # For branch_owner, get their assigned branch
        if self.request.user.role.role_type == 'branch_owner':
            if self.request.user.role.branch:
                return self.request.user.role.branch
            else:
                # Redirect to a page indicating they don't have a branch assigned
                return redirect('no_branch_assigned')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branch = self.object
        
        # Get all schemes under this branch
        schemes = Scheme.objects.filter(branch=branch)
        context['schemes'] = schemes
        
        # Get total policies count
        total_policies = Policy.objects.filter(scheme__in=schemes).count()
        context['total_policies'] = total_policies
        
        # Get monthly policies (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        monthly_policies = Policy.objects.filter(
            scheme__in=schemes, 
            created_at__gte=thirty_days_ago
        ).count()
        context['monthly_policies'] = monthly_policies
        
        # Calculate lapse percentage
        lapsed_policies = Policy.objects.filter(
            scheme__in=schemes,
            status='lapsed'
        ).count()
        if total_policies > 0:
            lapse_percentage = (lapsed_policies / total_policies) * 100
        else:
            lapse_percentage = 0
        context['lapse_percentage'] = round(lapse_percentage, 2)
        
        # Get all agents per scheme
        agents_by_scheme = {}
        for scheme in schemes:
            agents_by_scheme[scheme] = Agent.objects.filter(scheme=scheme)
        context['agents_by_scheme'] = agents_by_scheme
        
        # Get top performing schemes (this quarter)
        quarter_start = timezone.now().replace(
            month=(timezone.now().month - 1) // 3 * 3 + 1,
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        
        top_schemes = []
        for scheme in schemes:
            policies_count = Policy.objects.filter(
                scheme=scheme,
                created_at__gte=quarter_start
            ).count()
            
            top_schemes.append({
                'scheme': scheme,
                'policies_count': policies_count
            })
        
        # Sort by policies count (descending)
        top_schemes = sorted(top_schemes, key=lambda x: x['policies_count'], reverse=True)
        context['top_schemes'] = top_schemes[:5]  # Top 5 schemes
        
        # Check if user has AI insights access (internal_admin or branch_owner)
        user = self.request.user
        has_ai_access = False
        if hasattr(user, 'role'):
            role = user.role
            if role.role_type == 'internal_admin':
                has_ai_access = True
            elif role.role_type == 'branch_owner' and role.branch == branch:
                has_ai_access = True
        
        context['has_ai_access'] = has_ai_access
        context['ai_insights_url'] = f"/settings/dashboards/branch/{branch.id}/insights/"
        
        # Sample AI questions for branch insights
        context['sample_ai_questions'] = [
            "Which scheme has the highest lapse rate?",
            "What is the overall performance trend this quarter?",
            "Which schemes need attention due to high lapse rates?",
            "How many policies were added in the last month?"
        ]
        
        return context


class SchemeDashboardView(LoginRequiredMixin, SchemeAccessMixin, DetailView):
    """Dashboard view for a scheme showing performance metrics and agents"""
    model = Scheme
    template_name = 'settings_app/dashboards/scheme_dashboard.html'
    context_object_name = 'scheme'
    pk_url_kwarg = 'pk'
    
    def get_object(self, queryset=None):
        # For internal_admin, branch_owner, and compliance_auditor, get the scheme by ID
        if self.request.user.role.role_type in ['internal_admin', 'branch_owner', 'compliance_auditor']:
            return get_object_or_404(Scheme, pk=self.kwargs.get('pk'))
        
        # For scheme_manager, get their assigned scheme
        if self.request.user.role.role_type == 'scheme_manager':
            if self.request.user.role.scheme:
                return self.request.user.role.scheme
            else:
                # Redirect to a page indicating they don't have a scheme assigned
                return redirect('no_scheme_assigned')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scheme = self.object
        
        # Get all agents under this scheme
        agents = Agent.objects.filter(scheme=scheme)
        context['agents'] = agents
        
        # Get total applications
        total_applications = Policy.objects.filter(scheme=scheme).count()
        context['total_applications'] = total_applications
        
        # Calculate conversion percentage
        approved_policies = Policy.objects.filter(
            scheme=scheme,
            status__in=['active', 'approved']
        ).count()
        if total_applications > 0:
            conversion_percentage = (approved_policies / total_applications) * 100
        else:
            conversion_percentage = 0
        context['conversion_percentage'] = round(conversion_percentage, 2)
        
        # Calculate average cover amount
        policies = Policy.objects.filter(scheme=scheme, status='active')
        if policies.exists():
            avg_cover = policies.aggregate(Avg('cover_amount'))['cover_amount__avg']
        else:
            avg_cover = 0
        context['average_cover'] = round(avg_cover, 2)
        
        # Get linked plans
        plans = Plan.objects.filter(scheme=scheme)
        context['plans'] = plans
        
        # Check if user has AI insights access (internal_admin or scheme_manager)
        user = self.request.user
        has_ai_access = False
        if hasattr(user, 'role'):
            role = user.role
            if role.role_type == 'internal_admin':
                has_ai_access = True
            elif role.role_type == 'scheme_manager' and role.scheme == scheme:
                has_ai_access = True
            elif role.role_type == 'branch_owner' and scheme.branch == role.branch:
                has_ai_access = True
        
        context['has_ai_access'] = has_ai_access
        context['ai_insights_url'] = f"/settings/dashboards/scheme/{scheme.id}/insights/"
        
        # Sample AI questions for scheme insights
        context['sample_ai_questions'] = [
            "Who are my top performing agents?",
            "What is the conversion rate trend this month?",
            "Which agents need additional training based on performance?",
            "What is the average cover amount for policies sold this quarter?"
        ]
        
        # Check if user can see AI panel
        context['show_ai_panel'] = self.request.user.role.role_type in ['internal_admin', 'scheme_manager']
        
        return context


class AgentDetailView(LoginRequiredMixin, AgentAccessMixin, DetailView):
    """Detail view for an agent showing performance metrics and DIY link"""
    model = Agent
    template_name = 'settings_app/dashboards/agent_detail.html'
    context_object_name = 'agent'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent = self.object
        
        # Get total policies
        policies = Policy.objects.filter(agent=agent)
        total_policies = policies.count()
        context['total_policies'] = total_policies
        
        # Get monthly policies (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        monthly_policies = policies.filter(created_at__gte=thirty_days_ago).count()
        context['monthly_policies'] = monthly_policies
        
        # Get quarterly policies (last 90 days)
        ninety_days_ago = timezone.now() - timedelta(days=90)
        quarterly_policies = policies.filter(created_at__gte=ninety_days_ago).count()
        context['quarterly_policies'] = quarterly_policies
        
        # Calculate lapse percentage
        lapsed_policies = policies.filter(status='lapsed').count()
        if total_policies > 0:
            lapse_percentage = (lapsed_policies / total_policies) * 100
        else:
            lapse_percentage = 0
        context['lapse_percentage'] = round(lapse_percentage, 2)
        
        # Calculate average cover amount
        if policies.exists():
            avg_cover = policies.filter(status='active').aggregate(Avg('cover_amount'))['cover_amount__avg'] or 0
        else:
            avg_cover = 0
        context['average_cover'] = round(avg_cover, 2)
        
        # Generate DIY link
        base_url = self.request.build_absolute_uri('/').rstrip('/')
        
        # Create a token if one doesn't exist
        if not agent.diy_token:
            agent.diy_token = str(uuid.uuid4())
            agent.diy_token_created = timezone.now()
            agent.save()
            
        diy_link = f"{base_url}/apply/{agent.diy_token}/"
        context['diy_link'] = diy_link
        
        # Get policy statistics by month (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = []
        
        for i in range(6):
            month_start = timezone.now() - timedelta(days=30 * (i + 1))
            month_end = timezone.now() - timedelta(days=30 * i)
            
            # Get policies for this month
            month_policies = policies.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            )
            
            # Count total policies for the month
            month_policy_count = month_policies.count()
            
            # Count active and lapsed policies
            active_policies = month_policies.filter(status='active').count()
            lapsed_policies = month_policies.filter(status='lapsed').count()
            
            # Calculate lapse rate for the month
            if month_policy_count > 0:
                month_lapse_rate = round((lapsed_policies / month_policy_count) * 100, 2)
            else:
                month_lapse_rate = 0
            
            month_name = month_start.strftime('%B %Y')
            monthly_stats.append({
                'month': month_name,
                'count': month_policy_count,
                'active': active_policies,
                'lapsed': lapsed_policies,
                'lapse_rate': month_lapse_rate
            })
        
        # Reverse to show oldest to newest
        monthly_stats.reverse()
        context['monthly_stats'] = monthly_stats
        
        # Check if user is read-only
        context['is_read_only'] = self.request.user.role.role_type == 'compliance_auditor'
        
        # Get referral statistics if available
        context['total_referrals'] = getattr(agent, 'total_referrals', 0)
        context['conversion_rate'] = getattr(agent, 'conversion_rate', 0)
        
        return context


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
