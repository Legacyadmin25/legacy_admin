# settings_app/views/__init__.py

from .general import general_settings
from .plans import get_underwriter_for_plan
from .users import (
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
    import_users_view,
    user_template_download,
)

from .agent_dashboard import AgentDashboardView

from .branches import (
    BranchListView,
    BranchCreateView,
    BranchUpdateView,
    BranchDeleteView,
    export_branches_csv,
)

from .schemes import (
    SchemeListView,
    SchemeCreateView,
    SchemeUpdateView,
    SchemeDeleteView,
    upload_scheme_document,
    delete_scheme_document,
)

from .agents import (
    AgentListView,
    agent_setup,
    AgentDeleteView,
    export_agents_csv,
)

from .users import (
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
)

# SMS sending & templates were moved to members.communications; remove these imports:
# from .sms import (
#     sms_sending,
#     sms_template,
# )

from .underwriters import (
    UnderwriterListView,
)

from .permissions import (
    manage_rights_view,
)

from .plans import (
    PlanListView,
    PlanCreateView,
    PlanUpdateView,
    plan_deactivate,
    export_plans_csv,
    clone_plan,
    plan_template_download,
    plan_import,
    plan_delete,
)

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden


from django.contrib.auth.decorators import login_required

@login_required
def simple_create_plan(request):
    from django.utils import timezone
    from decimal import Decimal
    from schemes.models import Plan, Scheme
    
    # Show a simple form for GET requests
    if request.method == 'GET':
        schemes = Scheme.objects.all()
        return render(request, 'settings_app/simple_plan_form.html', {
            'schemes': schemes
        })
    
    # Process form submission for POST requests
    elif request.method == 'POST':
        try:
            # Get the scheme
            scheme_id = request.POST.get('scheme')
            if not scheme_id:
                messages.error(request, "Please select a scheme")
                return redirect('settings:simple_create_plan')
            
            scheme = Scheme.objects.get(pk=scheme_id)
            
            # Create the plan with ALL required fields explicitly set
            plan = Plan(
                scheme=scheme,
                name=request.POST.get('name', 'New Plan'),
                premium=Decimal('0.00'),        # Required field
                min_age=0,                      # Required field
                max_age=100,                    # Required field
                policy_type='service',          # Default policy type
                underwriter='',                 # Empty underwriter
                main_cover=Decimal('0.00'),     # Default value
                main_premium=Decimal('0.00'),   # Default value
                main_uw_cover=Decimal('0.00'),  # Default value
                main_uw_premium=Decimal('0.00'),# Default value
                main_age_from=0,               # Default value
                main_age_to=100,               # Default value
                waiting_period=6,              # Default value
                lapse_period=2,                # Default value
                max_dependents=0,              # Default value
                admin_fee=Decimal('0.00'),     # Default value
                cash_payout=Decimal('0.00'),   # Default value
                agent_commission=Decimal('0.00'), # Default value
                office_fee=Decimal('0.00'),    # Default value
                scheme_fee=Decimal('0.00'),    # Default value
                manager_fee=Decimal('0.00'),   # Default value
                loyalty_programme=Decimal('0.00'), # Default value
                other_fees=Decimal('0.00'),    # Default value
                penalty_fee=Decimal('0.00'),   # Default value
                service_fee=Decimal('0.00'),   # Default value
                is_active=True,                # Default value
                modified=timezone.now().date() # Default value
            )
            
            # Save the plan
            plan.save()
            
            messages.success(request, f"Plan '{plan.name}' created successfully!")
            return redirect('settings:plan')
            
        except Exception as e:
            messages.error(request, f"Error creating plan: {str(e)}")
            return redirect('settings:simple_create_plan')
    
    # Default response for other request methods
    return redirect('settings:plan')


class AgentDIYLinkView(LoginRequiredMixin, TemplateView):
    template_name = 'settings_app/agent_diy_link.html'

    def dispatch(self, request, *args, **kwargs):
        # Ensure the logged-in User actually has an Agent record
        try:
            self.agent = request.user.agent
        except ObjectDoesNotExist:
            return HttpResponseForbidden("You do not have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        agent = self.agent
        ctx['agent'] = agent

        if agent.diy_token:
            diy_path = reverse('members:diy_signup', args=[agent.diy_token])
            ctx['diy_link'] = self.request.build_absolute_uri(diy_path)
        else:
            ctx['diy_link'] = None

        return ctx

    def post(self, request, *args, **kwargs):
        agent = self.agent
        action = request.POST.get('action')
        if action == 'generate':
            agent.generate_diy_token()
            messages.success(request, "DIY link generated.")
        elif action == 'revoke':
            agent.revoke_diy_token()
            messages.success(request, "DIY link revoked.")
        return redirect('settings:agent_diy_link')
