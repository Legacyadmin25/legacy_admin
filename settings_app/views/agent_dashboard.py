from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, time, timedelta

from members.models import Policy
from members.models_public_enrollment import PublicApplication
from ..models import Agent


def _normalize_activity_timestamp(value):
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    if value is None:
        return timezone.now() - timedelta(days=3650)
    combined = datetime.combine(value, time.min)
    return timezone.make_aware(combined, timezone.get_current_timezone())


def _get_active_agent_policies(agent):
    today = timezone.now().date()
    return Policy.objects.filter(underwritten_by=agent).exclude(lapse_warning='lapsed').filter(
        cover_date__isnull=True
    ) | Policy.objects.filter(underwritten_by=agent).exclude(lapse_warning='lapsed').filter(
        cover_date__gte=today
    )


def _payment_allocation_model():
    return apps.get_model('payments', 'PaymentAllocation')

class AgentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'settings_app/agent_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the agent for the current user
        try:
            agent = Agent.objects.select_related('scheme').get(user=self.request.user)
            context['agent'] = agent
            current_month = timezone.now().date().replace(day=1)
            payment_allocation_model = _payment_allocation_model()

            policy_queryset = Policy.objects.filter(underwritten_by=agent).select_related('member', 'plan', 'scheme')
            active_policies_queryset = _get_active_agent_policies(agent).select_related('member', 'plan', 'scheme').distinct()
            public_application_queryset = PublicApplication.objects.filter(
                enrollment_link__agent=agent
            ).exclude(status='draft').select_related('plan', 'scheme', 'converted_policy', 'converted_member')
            direct_policy_referrals = policy_queryset.filter(source_application__isnull=True).values('member_id').distinct().count()
            application_referrals = public_application_queryset.count()
            commission_total = payment_allocation_model.objects.filter(
                agent=agent,
                payment__status='COMPLETED',
                allocation_status='ALLOCATED',
                coverage_month=current_month,
            ).aggregate(total=Sum('agent_commission'))['total'] or 0

            agent.referral_count = direct_policy_referrals + application_referrals
            agent.active_policies = active_policies_queryset.count()
            agent.commission_earned = commission_total
            context['diy_share_url'] = agent.get_short_diy_link(self.request) or agent.get_full_diy_link()

            recent_activity = []
            for policy in policy_queryset.order_by('-created_at', '-id')[:3]:
                timestamp = policy.created_at or policy.updated_at
                if timestamp:
                    recent_activity.append({
                        'title': 'Policy Signed Up',
                        'description': f"{policy.member.first_name} {policy.member.last_name} was linked to Policy #{policy.policy_number}",
                        'timestamp': timestamp,
                    })

            for allocation in payment_allocation_model.objects.filter(
                agent=agent,
                payment__status='COMPLETED',
                allocation_status='ALLOCATED',
            ).select_related('policy').order_by('-payment__date', '-id')[:3]:
                recent_activity.append({
                    'title': 'Commission Allocated',
                    'description': (
                        f"R{allocation.agent_commission:.2f} allocated from Policy "
                        f"#{allocation.policy.policy_number} for {allocation.coverage_month.strftime('%B %Y')}"
                    ),
                    'timestamp': allocation.payment.date,
                })

            for application in public_application_queryset.order_by('-submitted_at', '-created_at')[:3]:
                recent_activity.append({
                    'title': 'Public Application Submitted',
                    'description': f"{application.first_name} {application.last_name} submitted {application.application_id}",
                    'timestamp': application.submitted_at or application.created_at,
                })

            context['recent_activity'] = sorted(
                recent_activity,
                key=lambda item: _normalize_activity_timestamp(item['timestamp']),
                reverse=True,
            )[:6]
            
        except Agent.DoesNotExist:
            context['agent'] = None
            context['recent_activity'] = []
            context['diy_share_url'] = None
        
        return context
