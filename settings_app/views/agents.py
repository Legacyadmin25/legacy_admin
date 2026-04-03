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
    template_name = 'settings_app/agent_list.html'
    context_object_name = 'agents'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get schemes based on user role
        if user.is_superuser:
            ctx['schemes'] = Scheme.objects.all()
        elif user.groups.filter(name='Branch Owner').exists():
            ctx['schemes'] = Scheme.objects.filter(branch=user.userprofile.branch)
        elif user.groups.filter(name='Scheme Admin').exists():
            ctx['schemes'] = Scheme.objects.filter(admin_user=user)
        else:
            ctx['schemes'] = Scheme.objects.none()
            
        ctx['can_add_agent'] = user.is_superuser or user.groups.filter(name__in=['Branch Owner', 'Scheme Admin']).exists()
        return ctx

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        search_query = self.request.GET.get('q', '')
        
        # Filter by search query
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(surname__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(contact_number__icontains=search_query) |
                Q(scheme__name__icontains=search_query)
            )
        
        # Filter by user role
        if user.is_superuser:
            return queryset.select_related('scheme')
        elif user.groups.filter(name='Branch Owner').exists():
            return queryset.filter(scheme__branch=user.userprofile.branch).select_related('scheme')
        elif user.groups.filter(name='Scheme Admin').exists():
            return queryset.filter(scheme__admin_user=user).select_related('scheme')
        return queryset.none()


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


# ─── Agent Setup View (Create/Edit/List) ───────────────────────────────────────
@login_required
def agent_setup(request, pk=None):
    user = request.user
    instance = None
    edit_mode = bool(pk)  # True if we're editing an existing agent
    
    # Get schemes based on user role for the form
    if user.is_superuser:
        schemes = Scheme.objects.all()
    elif user.groups.filter(name='Branch Owner').exists():
        schemes = Scheme.objects.filter(branch=user.userprofile.branch)
    elif user.groups.filter(name='Scheme Admin').exists():
        schemes = Scheme.objects.filter(admin_user=user)
    else:
        schemes = Scheme.objects.none()
    
    # Handle editing an existing agent
    if pk:
        instance = get_object_or_404(Agent, pk=pk)
        
        # Check permissions
        if not user.is_superuser:
            if user.groups.filter(name='Branch Owner').exists() and instance.scheme and instance.scheme.branch != user.userprofile.branch:
                raise PermissionDenied("You don't have permission to edit this agent.")
            elif user.groups.filter(name='Scheme Admin').exists() and instance.scheme and instance.scheme.admin_user != user:
                raise PermissionDenied("You don't have permission to edit this agent.")
    
    # Handle form submission
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            try:
                # For new agents, save directly to avoid primary key issues
                agent = form.save()
                
                # For existing agents, we don't need special handling
                # The form.save() above will handle both new and existing agents correctly
                
                messages.success(request, f"Agent '{agent.full_name}' {'updated' if edit_mode else 'created'} successfully!")
                return redirect('settings:agent')
            except Exception as e:
                messages.error(request, f"Error saving agent: {str(e)}")
        else:
            # Log form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Create a form for the agent setup page
        form = AgentForm(instance=instance, user=user)
    
    # Get agents for the list view
    agents = get_agents_based_on_permissions(user)
    
    # Determine if we're on the edit/create page
    # Force is_edit_page to True when we're on the create URL
    is_edit_page = 'add' in request.path or pk is not None
    
    context = {
        'agents': agents,
        'schemes': schemes,
        'can_add_agent': user.is_superuser or user.groups.filter(name__in=['Branch Owner', 'Scheme Admin']).exists(),
        'form': form,
        'edit_mode': edit_mode,
        'is_edit_page': is_edit_page
    }
    
    return render(request, 'settings_app/agent_setup.html', context)


# ─── Agent Create View ─────────────────────────────────────────────
@login_required
def agent_create(request):
    user = request.user
    
    # Get schemes based on user role for the form
    if user.is_superuser:
        schemes = Scheme.objects.all()
    elif user.groups.filter(name='Branch Owner').exists():
        schemes = Scheme.objects.filter(branch=user.userprofile.branch)
    elif user.groups.filter(name='Scheme Admin').exists():
        schemes = Scheme.objects.filter(admin_user=user)
    else:
        schemes = Scheme.objects.none()
    
    # Handle form submission
    if request.method == 'POST':
        form = AgentForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                agent = form.save(commit=False)
                # Set created_by for new agents
                agent.created_by = user
                agent.save()
                form.save_m2m()  # Save many-to-many fields if any
                
                messages.success(request, f"Agent '{agent.full_name}' created successfully!")
                return redirect('settings:agent')
            except Exception as e:
                messages.error(request, f"Error saving agent: {str(e)}")
        else:
            # Log form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Create a new form for the agent create page
        form = AgentForm(user=user)
    
    context = {
        'schemes': schemes,
        'can_add_agent': user.is_superuser or user.groups.filter(name__in=['Branch Owner', 'Scheme Admin']).exists(),
        'form': form,
        'edit_mode': False,  # This is a create page, not edit
        'is_edit_page': True  # This is an edit page (as opposed to list view)
    }
    
    return render(request, 'settings_app/agent_setup_new.html', context)


# ─── Agent Edit View ─────────────────────────────────────────────
@login_required
def agent_edit(request, pk):
    user = request.user
    
    # Get schemes based on user role for the form
    if user.is_superuser:
        schemes = Scheme.objects.all()
    elif user.groups.filter(name='Branch Owner').exists():
        schemes = Scheme.objects.filter(branch=user.userprofile.branch)
    elif user.groups.filter(name='Scheme Admin').exists():
        schemes = Scheme.objects.filter(admin_user=user)
    else:
        schemes = Scheme.objects.none()
    
    # Get the agent instance
    instance = get_object_or_404(Agent, pk=pk)
    
    # Check permissions
    if not user.is_superuser:
        if user.groups.filter(name='Branch Owner').exists() and instance.scheme and instance.scheme.branch != user.userprofile.branch:
            raise PermissionDenied("You don't have permission to edit this agent.")
        elif user.groups.filter(name='Scheme Admin').exists() and instance.scheme and instance.scheme.admin_user != user:
            raise PermissionDenied("You don't have permission to edit this agent.")
    
    # Handle form submission
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            try:
                agent = form.save()
                messages.success(request, f"Agent '{agent.full_name}' updated successfully!")
                return redirect('settings:agent')
            except Exception as e:
                messages.error(request, f"Error saving agent: {str(e)}")
        else:
            # Log form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Create a form for editing the agent
        form = AgentForm(instance=instance, user=user)
    
    context = {
        'schemes': schemes,
        'can_add_agent': user.is_superuser or user.groups.filter(name__in=['Branch Owner', 'Scheme Admin']).exists(),
        'form': form,
        'edit_mode': True,  # This is an edit page
        'is_edit_page': True  # This is an edit page (as opposed to list view)
    }
    
    return render(request, 'settings_app/agent_setup_new.html', context)


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
    # Redirect back to the edit page instead of the list view
    return redirect('settings:agent_edit', pk=agent_id)
