from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib.auth.models import Group
from django.db.models import Q
import csv
from settings_app.models import Agent
from schemes.models import Scheme
from settings_app.forms import AgentForm
from django.contrib.auth.decorators import login_required  # <-- Add this import
import csv


# ─── Agent List View ───────────────────────────────────────────────────────
class AgentListView(LoginRequiredMixin, ListView):
    model = Agent
    template_name = 'settings_app/agent_list.html'  # <-- ensure this matches the actual template
    context_object_name = 'agents'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schemes'] = Scheme.objects.all()  # Optional: provide Scheme queryset if filtering
        return ctx

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Agent.objects.all()
        elif user.groups.filter(name='Branch Owner').exists():
            return Agent.objects.filter(scheme__branch=user.userprofile.branch)
        elif user.groups.filter(name='Scheme Admin').exists():
            return Agent.objects.filter(scheme__admin_user=user)
        return Agent.objects.none()


# ─── Agent Create View ───────────────────────────────────────────────────────
class AgentCreateView(LoginRequiredMixin, CreateView):
    model = Agent
    form_class = AgentForm
    template_name = 'settings_app/agent_setup.html'
    success_url = reverse_lazy('settings:agent')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Agent created successfully.")
        return redirect(self.success_url)


# ─── Agent Update View ───────────────────────────────────────────────────────
class AgentUpdateView(LoginRequiredMixin, UpdateView):
    model = Agent
    form_class = AgentForm
    template_name = 'settings_app/agent_setup.html'
    success_url = reverse_lazy('settings:agent')

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Agent.objects.all()
        elif user.groups.filter(name='Branch Owner').exists():
            return Agent.objects.filter(scheme__branch=user.userprofile.branch)
        elif user.groups.filter(name='Scheme Admin').exists():
            return Agent.objects.filter(scheme__admin_user=user)
        return Agent.objects.none()

    def form_valid(self, form):
        messages.success(self.request, "Agent updated successfully.")
        return super().form_valid(form)


# ─── Agent Delete View ───────────────────────────────────────────────────────
class AgentDeleteView(LoginRequiredMixin, DeleteView):
    model = Agent
    template_name = 'settings_app/agent_confirm_delete.html'
    success_url = reverse_lazy('settings:agent')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Agent deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ─── Agent Setup View ───────────────────────────────────────────────────────
@login_required
def agent_setup(request):
    user = request.user
    if request.method == 'POST':
        form = AgentForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Agent created successfully.")
            return redirect('settings:agent')
    else:
        form = AgentForm(user=user)

    agents = get_agents_based_on_permissions(user)

    return render(request, 'settings_app/agent_setup.html', {
        'form': form,
        'agents': agents,
        'edit_mode': False,
    })


# ─── Helper function to handle agent permissions ─────────────────────────────
def get_agents_based_on_permissions(user):
    if user.is_superuser:
        return Agent.objects.select_related('scheme').all()
    if user.groups.filter(name='Branch Owner').exists():
        return Agent.objects.filter(scheme__branch=user.userprofile.branch)
    if user.groups.filter(name='Scheme Admin').exists():
        return Agent.objects.filter(scheme__admin_user=user)
    return Agent.objects.none()


# ─── Bulk Agent Actions ─────────────────────────────────────────────────────
@login_required
def bulk_agent_actions(request):
    action = request.POST.get("action")
    agent_ids = request.POST.getlist("agent_ids")
    scheme_id = request.POST.get("scheme_id")

    if not agent_ids:
        messages.warning(request, "No agents selected.")
        return redirect("settings:agent")

    agents = Agent.objects.filter(id__in=agent_ids)

    if action == "deactivate":
        agents.update(user=None)
        messages.success(request, f"{agents.count()} agent(s) deactivated.")
    elif action == "assign_scheme":
        if scheme_id:
            scheme = get_object_or_404(Scheme, id=scheme_id)
            agents.update(scheme=scheme)
            messages.success(request, f"Assigned {agents.count()} agent(s) to scheme: {scheme.name}")
        else:
            messages.error(request, "No scheme selected.")

    return redirect("settings:agent")


# ─── Export Agents to CSV ───────────────────────────────────────────────────
@login_required
def export_agents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="agents.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Full Name', 'Surname', 'Scheme', 'Commission %', 'Rand Value', 'Contact', 'Email'
    ])

    for agent in Agent.objects.all():
        writer.writerow([
            agent.full_name, agent.surname,
            agent.scheme.name if agent.scheme else '',
            agent.commission_percentage or '',
            agent.commission_rand_value or '',
            agent.contact_number, agent.email,
        ])

    return response


# ─── Agent Regenerate DIY Token ─────────────────────────────────────────────
@login_required
def regenerate_diy_token(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    agent.revoke_diy_token()
    agent.generate_diy_token()
    messages.success(request, f"New DIY token generated for {agent.full_name}.")
    return redirect('settings:agent')
