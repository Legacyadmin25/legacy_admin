# settings_app/views/plans.py

import csv
import json
import logging
from copy import deepcopy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.forms import forms
from schemes.models import Plan as SchemePlan, Scheme
from settings_app.models import PlanMemberTier, Underwriter
from settings_app.forms import PlanForm, PlanMemberTierFormSet
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.generic import ListView
from django.utils.decorators import method_decorator

# Set up logging
logger = logging.getLogger(__name__)
from settings_app.utils.openai_helper import suggest_tiers_from_description, format_suggested_tiers

from django.views.generic import ListView
from schemes.models import Plan

class PlanListView(ListView):
    model = Plan
    template_name = 'settings_app/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('scheme')
        selected_scheme = self.request.GET.get('scheme')
        if selected_scheme:
            queryset = queryset.filter(scheme_id=selected_scheme)
        else:
            queryset = queryset.none()
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_plans_count'] = Plan.objects.filter(is_active=True).count()
        context['total_plans'] = Plan.objects.count()
        context['schemes'] = Scheme.objects.order_by('name')
        context['selected_scheme'] = self.request.GET.get('scheme', '')
        return context

# [Previous functions and classes remain the same until PlanCreateView]

class PlanCreateView(LoginRequiredMixin, View):
    """View for creating a new plan with member tiers"""
    
    def get(self, request):
        initial_data = {
            'main_cover': 0,
            'main_premium': 0,
            'main_age_from': 0,
            'main_age_to': 99,
            'waiting_period': 6,  # Default waiting period
            'lapse_period': 2,    # Default lapse period
            'admin_fee': 0,
            'cash_payout': 0,
            'agent_commission': 0,
            'office_fee': 0,
            'scheme_fee': 0,
            'manager_fee': 0,
            'loyalty_programme': 0,
            'other_fees': 0,
            'is_active': True
        }
        selected_scheme = request.GET.get('scheme')
        if selected_scheme:
            initial_data['scheme'] = selected_scheme

        form = PlanForm(initial=initial_data)
        
        # Initialize the formset with the prefix
        formset = PlanMemberTierFormSet(
            queryset=PlanMemberTier.objects.none(),
            prefix='tiers'
        )
        
        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
            'section_fields': [
                ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                ("Other Settings", ['is_active','is_diy_visible']),
            ],
        })
    
    def post(self, request):
        form = PlanForm(request.POST, request.FILES)
        formset = PlanMemberTierFormSet(request.POST, prefix='tiers')
        
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        if form.is_valid() and formset.is_valid():
            try:
                plan = form.save()
                tiers = formset.save(commit=False)
                for tier in tiers:
                    tier.plan = plan
                    tier.save()
                formset.save_m2m()
                
                messages.success(request, 'Plan created successfully!')
                
                if is_htmx:
                    response = HttpResponse(status=200)
                    response['HX-Redirect'] = reverse('settings:plan')
                    return response
                else:
                    return redirect('settings:plan')
            except Exception as e:
                messages.error(request, f'Error saving plan: {str(e)}')
                if is_htmx:
                    return render(request, 'settings_app/plan_form.html', {
                        'form': form,
                        'formset': formset,
                        'empty_form': formset.empty_form,
                        'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
                        'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
                        'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
                        'other_fields': ['is_active'],
                        'section_fields': [
                            ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                            ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                            ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                            ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                            ("Other Settings", ['is_active','is_diy_visible']),
                        ],
                    }, status=422) # Unprocessable Entity status for validation errors
        
        # If invalid, re-render the form with errors
        context = {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
            'section_fields': [
                ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                ("Other Settings", ['is_active','is_diy_visible']),
            ],
            'form_errors': True,
        }
        
        if is_htmx:
            return render(request, 'settings_app/plan_form.html', context, status=422)
        else:
            return render(request, 'settings_app/plan_form.html', context)

def get_underwriter_for_plan(request):
    """AJAX endpoint to get underwriter details for a plan"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        plan_id = request.GET.get('plan_id')
        try:
            plan = Plan.objects.get(id=plan_id)
            underwriter = plan.underwriter
            if underwriter:
                return JsonResponse({
                    'status': 'success',
                    'underwriter_id': underwriter.id,
                    'underwriter_name': str(underwriter),
                })
            return JsonResponse({'status': 'not_found'}, status=404)
        except (Plan.DoesNotExist, ValueError):
            return JsonResponse({'status': 'error', 'message': 'Plan not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

class PlanUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        form = PlanForm(instance=plan)
        formset = PlanMemberTierFormSet(queryset=PlanMemberTier.objects.filter(plan=plan), prefix='tiers')
        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'edit_mode': True,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
            'section_fields': [
                ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                ("Other Settings", ['is_active','is_diy_visible']),
            ],
        })

    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        form = PlanForm(request.POST, request.FILES, instance=plan)
        formset = PlanMemberTierFormSet(request.POST, queryset=PlanMemberTier.objects.filter(plan=plan), prefix='tiers')
        
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    messages.success(request, 'Plan updated successfully!')
                    
                    if is_htmx:
                        response = HttpResponse(status=200)
                        response['HX-Redirect'] = reverse('settings:plan')
                        return response
                    else:
                        return redirect('settings:plan')
            except Exception as e:
                messages.error(request, f'Error updating plan: {str(e)}')
                if is_htmx:
                    return render(request, 'settings_app/plan_form.html', {
                        'form': form,
                        'formset': formset,
                        'edit_mode': True,
                        'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
                        'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
                        'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
                        'other_fields': ['is_active'],
                        'section_fields': [
                            ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                            ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                            ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                            ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                            ("Other Settings", ['is_active','is_diy_visible']),
                        ],
                    }, status=422) # Unprocessable Entity status for validation errors
        
        # If invalid, re-render the form with errors
        context = {
            'form': form,
            'formset': formset,
            'edit_mode': True,
            'form_errors': True,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
            'section_fields': [
                ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                ("Member Allowances", ['spouses_allowed','children_allowed','extended_allowed']),
                ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
                ("Other Settings", ['is_active','is_diy_visible']),
            ],
        }
        
        if is_htmx:
            return render(request, 'settings_app/plan_form.html', context, status=422)
        else:
            return render(request, 'settings_app/plan_form.html', context)

def plan_deactivate(request, pk):
    """Simple view to deactivate a plan"""
    plan = get_object_or_404(Plan, pk=pk)
    plan.is_active = False
    plan.save()
    messages.success(request, f'Plan "{plan.name}" has been deactivated.')
    return redirect('settings:plan')


def clone_plan(request, pk):
    """Clone an existing plan"""
    source_plan = get_object_or_404(Plan, pk=pk)
    
    # Create a new plan with similar attributes
    new_plan = Plan.objects.create(
        name=f"Copy of {source_plan.name}",
        description=source_plan.description,
        policy_type=source_plan.policy_type,
        scheme=source_plan.scheme,
        underwriter=source_plan.underwriter,
        main_cover=source_plan.main_cover,
        main_premium=source_plan.main_premium,
        main_uw_cover=source_plan.main_uw_cover,
        main_uw_premium=source_plan.main_uw_premium,
        main_age_from=source_plan.main_age_from,
        main_age_to=source_plan.main_age_to,
        waiting_period=source_plan.waiting_period,
        lapse_period=source_plan.lapse_period,
        spouses_allowed=source_plan.spouses_allowed,
        children_allowed=source_plan.children_allowed,
        extended_allowed=source_plan.extended_allowed,
        admin_fee=source_plan.admin_fee,
        cash_payout=source_plan.cash_payout,
        agent_commission=source_plan.agent_commission,
        office_fee=source_plan.office_fee,
        scheme_fee=source_plan.scheme_fee,
        manager_fee=source_plan.manager_fee,
        loyalty_programme=source_plan.loyalty_programme,
        other_fees=source_plan.other_fees,
        is_active=True,
        created_by=request.user
    )
    
    # Clone the tiers
    for tier in PlanMemberTier.objects.filter(plan=source_plan):
        PlanMemberTier.objects.create(
            plan=new_plan,
            user_type=tier.user_type,
            age_from=tier.age_from,
            age_to=tier.age_to,
            cover=tier.cover,
            premium=tier.premium,
            uw_cover=tier.uw_cover,
            uw_premium=tier.uw_premium,
            extended_commission=tier.extended_commission
        )
    
    messages.success(request, f'Plan "{source_plan.name}" has been cloned.')
    return redirect('settings:plan')


def export_plans_csv(request):
    """Export all plans to CSV format"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plans_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'name', 'description', 'policy_type', 'scheme', 'underwriter', 
        'main_cover', 'main_premium', 'main_uw_cover', 'main_uw_premium', 
        'main_age_from', 'main_age_to', 'waiting_period', 'lapse_period',
        'spouses_allowed', 'children_allowed', 'extended_allowed',
        'admin_fee', 'cash_payout', 'agent_commission', 'office_fee', 
        'scheme_fee', 'manager_fee', 'loyalty_programme', 'other_fees',
        'is_active', 'created_at'
    ])

    plans = Plan.objects.all().select_related('scheme', 'underwriter')
    for plan in plans:
        writer.writerow([
            plan.name, plan.description, plan.policy_type, 
            plan.scheme.name if plan.scheme else '', 
            plan.underwriter.name if plan.underwriter else '',
            plan.main_cover, plan.main_premium, 
            plan.main_uw_cover, plan.main_uw_premium,
            plan.main_age_from, plan.main_age_to, 
            plan.waiting_period, plan.lapse_period,
            plan.spouses_allowed, plan.children_allowed, plan.extended_allowed,
            plan.admin_fee, plan.cash_payout, plan.agent_commission, 
            plan.office_fee, plan.scheme_fee, plan.manager_fee,
            plan.loyalty_programme, plan.other_fees,
            'Yes' if plan.is_active else 'No', 
            plan.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


def plan_template_download(request):
    """Provide a template CSV for plan imports"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plan_import_template.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'name', 'description', 'policy_type', 'underwriter', 
        'main_cover', 'main_premium', 'main_uw_cover', 'main_uw_premium', 
        'main_age_from', 'main_age_to', 'waiting_period', 'lapse_period',
        'spouses_allowed', 'children_allowed', 'extended_allowed',
        'admin_fee', 'cash_payout', 'agent_commission', 'office_fee', 
        'scheme_fee', 'manager_fee', 'loyalty_programme', 'other_fees',
        'is_active'
    ])
    
    # Add sample row
    writer.writerow([
        'Sample Plan', 'This is a sample plan', 'funeral', 'Sample Underwriter',
        '10000', '100', '10000', '80', '18', '65', '6', '2',
        '1', '4', '0', '10', '10', '20', '5', '5', '5', '5', '0', 'Yes'
    ])

    return response


def plan_import(request):
    """Import plans from a CSV file"""
    if request.method == 'POST':
        form = PlanImportForm(request.POST, request.FILES)
        if form.is_valid():
            scheme = form.cleaned_data['scheme']
            csv_file = request.FILES['file']
            
            # Basic validation - check if it's a CSV file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file.')
                return redirect('settings:plan_import')
            
            # Process the file
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(decoded_file)
            
            # Track import results
            plans_created = 0
            errors = []
            
            for i, row in enumerate(reader, start=1):
                try:
                    # Create plan instance but don't save yet
                    plan = Plan(
                        scheme=scheme,
                        name=row.get('name', f'Imported Plan {i}'),
                        description=row.get('description', ''),
                        policy_type=row.get('policy_type', 'funeral'),
                        main_cover=Decimal(row.get('main_cover', 0) or 0),
                        main_premium=Decimal(row.get('main_premium', 0) or 0),
                        main_uw_cover=Decimal(row.get('main_uw_cover', 0) or 0),
                        main_uw_premium=Decimal(row.get('main_uw_premium', 0) or 0),
                        main_age_from=int(row.get('main_age_from', 0) or 0),
                        main_age_to=int(row.get('main_age_to', 99) or 99),
                        waiting_period=int(row.get('waiting_period', 6) or 6),
                        lapse_period=int(row.get('lapse_period', 2) or 2),
                        spouses_allowed=int(row.get('spouses_allowed', 0) or 0),
                        children_allowed=int(row.get('children_allowed', 0) or 0),
                        extended_allowed=int(row.get('extended_allowed', 0) or 0),
                        admin_fee=Decimal(row.get('admin_fee', 0) or 0),
                        cash_payout=Decimal(row.get('cash_payout', 0) or 0),
                        agent_commission=Decimal(row.get('agent_commission', 0) or 0),
                        office_fee=Decimal(row.get('office_fee', 0) or 0),
                        scheme_fee=Decimal(row.get('scheme_fee', 0) or 0),
                        manager_fee=Decimal(row.get('manager_fee', 0) or 0),
                        loyalty_programme=Decimal(row.get('loyalty_programme', 0) or 0),
                        other_fees=Decimal(row.get('other_fees', 0) or 0),
                        is_active=row.get('is_active', 'Yes').lower() in ['yes', 'true', '1'],
                        created_by=request.user
                    )
                    
                    # Handle the underwriter if provided
                    underwriter_name = row.get('underwriter')
                    if underwriter_name:
                        underwriter, created = Underwriter.objects.get_or_create(
                            name=underwriter_name
                        )
                        plan.underwriter = underwriter
                    
                    # Save the plan
                    plan.save()
                    plans_created += 1
                    
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
            
            # Show results
            if plans_created > 0:
                messages.success(request, f'{plans_created} plans were successfully imported.')
            
            if errors:
                messages.warning(request, f'{len(errors)} rows had errors: ' + ', '.join(errors[:5]) + 
                               ('...' if len(errors) > 5 else ''))
            
            return redirect('settings:plan')
    else:
        form = PlanImportForm()
    
    return render(request, 'settings_app/plan_import.html', {
        'form': form
    })


def plan_delete(request, pk):
    """Delete a plan"""
    plan = get_object_or_404(Plan, pk=pk)
    name = plan.name
    plan.delete()
    messages.success(request, f'Plan "{name}" has been deleted.')
    return redirect('settings:plan')
