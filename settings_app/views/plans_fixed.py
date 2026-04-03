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

# [Previous functions and classes remain the same until PlanCreateView]

class PlanCreateView(LoginRequiredMixin, View):
    """View for creating a new plan with member tiers"""
    
    def get(self, request):
        form = PlanForm(initial={
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
        })
        
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
        # [Rest of the post method remains the same]
        pass

# [Rest of the file remains the same]
