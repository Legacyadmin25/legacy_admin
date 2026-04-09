from django.shortcuts import get_object_or_404, redirect

from members.models_public_enrollment import EnrollmentLink
from settings_app.models import Agent


def enrollment_short_redirect(request, link_id):
    link = get_object_or_404(EnrollmentLink, pk=link_id)
    return redirect(link.get_apply_url(request))


def diy_short_redirect(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    if not agent.diy_token:
        agent.generate_diy_token()
    return redirect('members:diy_signup_start', token=agent.diy_token)
