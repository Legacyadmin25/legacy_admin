# settings_app/views/plans.py

import csv
import json
from copy import deepcopy
from decimal import Decimal
from django.shortcuts            import render, redirect, get_object_or_404
from django.http                 import HttpResponse, JsonResponse
from django.contrib              import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins    import LoginRequiredMixin
from django.utils                import timezone
from django.views                import View
from django.views.generic        import ListView
from django.utils.decorators     import method_decorator
from django.db                   import transaction

# ← CORRECT Plan import—always use the one from schemes.models
from schemes.models import Plan, Scheme
from settings_app.models import PlanMemberTier, Underwriter
from settings_app.forms import PlanForm, PlanMemberTierFormSet, PlanImportForm
from settings_app.utils.openai_helper import suggest_tiers_from_description, format_suggested_tiers

# Direct plan creation function that bypasses form validation
def direct_create_plan(post_data, scheme_id):
    try:
        # Get the scheme
        scheme = Scheme.objects.get(pk=scheme_id)
        
        # Create a new plan
        plan = Plan(
            scheme=scheme,
            name=post_data.get('name', 'New Plan'),
            description=post_data.get('description', ''),
            policy_type=post_data.get('policy_type', 'service'),
            premium=Decimal(post_data.get('premium', 0) or 0),
            underwriter=post_data.get('underwriter', ''),
            min_age=int(post_data.get('min_age', 0) or 0),
            max_age=int(post_data.get('max_age', 100) or 100),
            main_cover=Decimal(post_data.get('main_cover', 0) or 0),
            main_premium=Decimal(post_data.get('main_premium', 0) or 0),
            main_uw_cover=Decimal(post_data.get('main_uw_cover', 0) or 0),
            main_uw_premium=Decimal(post_data.get('main_uw_premium', 0) or 0),
            main_age_from=int(post_data.get('main_age_from', 0) or 0),
            main_age_to=int(post_data.get('main_age_to', 100) or 100),
            waiting_period=int(post_data.get('waiting_period', 6) or 6),
            lapse_period=int(post_data.get('lapse_period', 2) or 2),
            spouses_allowed=int(post_data.get('spouses_allowed', 0) or 0),
            children_allowed=int(post_data.get('children_allowed', 0) or 0),
            extended_allowed=int(post_data.get('extended_allowed', 0) or 0),
            admin_fee=Decimal(post_data.get('admin_fee', 0) or 0),
            cash_payout=Decimal(post_data.get('cash_payout', 0) or 0),
            agent_commission=Decimal(post_data.get('agent_commission', 0) or 0),
            office_fee=Decimal(post_data.get('office_fee', 0) or 0),
            scheme_fee=Decimal(post_data.get('scheme_fee', 0) or 0),
            manager_fee=Decimal(post_data.get('manager_fee', 0) or 0),
            loyalty_programme=Decimal(post_data.get('loyalty_programme', 0) or 0),
            other_fees=Decimal(post_data.get('other_fees', 0) or 0),
            is_active=True,
            modified=timezone.now().date(),
        )
        
        # Save the plan
        plan.save()
        print(f"Plan created with ID: {plan.id}")
        
        # Process member tiers if any
        # This is simplified and doesn't handle formsets
        
        return plan
    except Exception as e:
        print(f"Error in direct_create_plan: {e}")
        return None


class PlanListView(LoginRequiredMixin, ListView):
    model = Plan
    template_name = 'settings_app/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 25

   
    def get_queryset(self):
        print("!!! PLAN LIST VIEW GET CALLED !!!")
        # we can now select_related both FKs
        qs = super().get_queryset().select_related('scheme')
        scheme_id = self.request.GET.get('scheme')
        if scheme_id:
            qs = qs.filter(scheme_id=scheme_id)
        return qs.order_by('-modified')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schemes'] = Scheme.objects.all()
        ctx['selected_scheme'] = self.request.GET.get('scheme', '')
        return ctx


@method_decorator(login_required, name='dispatch')
class PlanCreateView(LoginRequiredMixin, View):
    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("PlanCreateView GET called")
        
        # Check if we're requesting tier suggestions
        suggest = request.GET.get('suggest', 'false').lower() == 'true'
        plan_name = request.GET.get('name', '')
        description = request.GET.get('description', '')
        policy_type = request.GET.get('policy_type', 'service')
        premium = request.GET.get('premium', '0')
        
        form = PlanForm()
        formset = PlanMemberTierFormSet(queryset=PlanMemberTier.objects.none())
        
        # If suggestion is requested and we have a description
        suggested_tiers = []
        if suggest and description:
            try:
                # Convert premium to float for the API call
                premium_float = float(Decimal(premium.replace('R', '').replace(',', '') or '0'))
                
                # Get tier suggestions from OpenAI
                raw_suggestions = suggest_tiers_from_description(
                    plan_name, description, policy_type, premium_float
                )
                
                # Format the suggestions for the form
                suggested_tiers = format_suggested_tiers(raw_suggestions)
                
                if suggested_tiers:
                    messages.success(request, f"Generated {len(suggested_tiers)} tier suggestions based on the plan description.")
                else:
                    messages.info(request, "Could not generate tier suggestions. Please add tiers manually.")
            except Exception as e:
                logger.error(f"Error suggesting tiers: {str(e)}")
                messages.error(request, "An error occurred while generating tier suggestions.")
        
        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'edit_mode': False,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
            'suggested_tiers': suggested_tiers,
        })

    def post(self, request):
        """
        Enhanced plan creation with improved tier handling and validation
        """
        # Process the form data
        form = PlanForm(request.POST)
        formset = PlanMemberTierFormSet(request.POST)
        
        # Validate the form (basic validation)
        if not form.is_valid():
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'settings_app/plan_form.html', {
                'form': form,
                'formset': formset,
                'empty_form': formset.empty_form,
                'edit_mode': False,
                'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
                'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
                'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
                'other_fields': ['is_active'],
            })
        
        try:
            # Begin a transaction to ensure all related data is saved together
            with transaction.atomic():
                # Create the plan from form data
                plan = form.save(commit=False)
                
                # Set creation date
                plan.created = timezone.now()
                plan.modified = timezone.now()
                
                # Save the plan to get an ID
                plan.save()
                
                # Process the tier formset
                if formset.is_valid():
                    # Save the tiers but don't commit yet (we need to set the plan)
                    instances = formset.save(commit=False)
                    
                    # Track allowances for each type
                    spouse_count = 0
                    child_count = 0
                    extended_count = 0
                    
                    # Process each tier and set the plan
                    for tier in instances:
                        tier.plan = plan
                        
                        # Get the allowed value from the form data
                        form_index = formset.forms.index(formset.forms[instances.index(tier)])
                        allowed_value = int(request.POST.get(f'allowed_{form_index}', '0') or 0)
                        
                        # Update member allowances based on user type
                        if tier.user_type == 'Spouse':
                            spouse_count = max(spouse_count, allowed_value)
                        elif tier.user_type == 'Child':
                            child_count = max(child_count, allowed_value)
                        elif tier.user_type in ['Extended', 'Extended Child']:
                            extended_count = max(extended_count, allowed_value)
                        
                        # Save the tier
                        tier.save()
                    
                    # Process any deleted tiers
                    for obj in formset.deleted_objects:
                        obj.delete()
                    
                    # Update the plan with the calculated allowances
                    plan.spouses_allowed = spouse_count
                    plan.children_allowed = child_count
                    plan.extended_allowed = extended_count
                    plan.save()
                else:
                    # If formset is not valid, log the errors but continue
                    for form in formset:
                        for field, errors in form.errors.items():
                            for error in errors:
                                print(f"Tier form error: {field} - {error}")
                
                # Process any additional member data from hidden inputs
                try:
                    # Look for any hidden member_allowed inputs
                    member_allowed_data = {}
                    for key, value in request.POST.items():
                        if key.startswith('member_allowed_'):
                            try:
                                data = json.loads(value)
                                member_allowed_data[data['type']] = int(data['allowed'])
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
                    
                    # Update plan allowances if needed
                    if 'Spouse' in member_allowed_data and member_allowed_data['Spouse'] > plan.spouses_allowed:
                        plan.spouses_allowed = member_allowed_data['Spouse']
                    if 'Child' in member_allowed_data and member_allowed_data['Child'] > plan.children_allowed:
                        plan.children_allowed = member_allowed_data['Child']
                    if 'Extended' in member_allowed_data and member_allowed_data['Extended'] > plan.extended_allowed:
                        plan.extended_allowed = member_allowed_data['Extended']
                    
                    # Save plan with any updated allowances
                    plan.save()
                except Exception as e:
                    print(f"Error processing additional member data: {e}")
            
            messages.success(request, "Plan created successfully.")
            return redirect('settings:plan')
            
        except Exception as e:
            messages.error(request, f"Error creating plan: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating plan: {str(e)}", exc_info=True)
            
            # If we get here, render the form again
            return render(request, 'settings_app/plan_form.html', {
                'form': form,
                'formset': formset,
                'empty_form': formset.empty_form,
                'edit_mode': False,
                'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
                'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
                'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
                'other_fields': ['is_active'],
            })
        
        # If we get here, either form validation failed or an exception occurred
        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'edit_mode': False,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
        })
        for i, fs in enumerate(formset):
            print(f'DEBUG: Formset form {i} errors:', fs.errors)
        print('DEBUG: Formset non_form_errors:', formset.non_form_errors())

        if form.is_valid() and formset.is_valid():
            plan = form.save(commit=False)
            plan.created = timezone.now()
            plan.modified = timezone.now()
            plan.save()
            formset.instance = plan
            formset.save()
            messages.success(request, "Plan created successfully.")
            return redirect('settings:plan')
        else:
            messages.error(request, "Please fix the errors below.")
            # Debug: Show all form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Form error in '{field}': {error}")
            for error in form.non_field_errors():
                messages.error(request, f"Form non-field error: {error}")
            # Debug: Show all formset errors
            for formset_form in formset:
                for field, errors in formset_form.errors.items():
                    for error in errors:
                        messages.error(request, f"Formset error in '{field}': {error}")
            for error in formset.non_form_errors():
                messages.error(request, f"{error}")

        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'edit_mode': False,
            'section_fields': [
                ("Plan Information", ['name','description','policy_type','scheme','underwriter','code']),
                ("Policy Details", ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period','max_dependents']),
                ("Fee Distribution", ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees']),
            ],
            'extra_fields': ['penalty_fee','service_fee','is_active'],
        })



@method_decorator(login_required, name='dispatch')
class PlanUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        form = PlanForm(instance=plan)
        formset = PlanMemberTierFormSet(instance=plan)
        return render(request, 'settings_app/plan_form.html', {
            'form': form,
            'formset': formset,
            'empty_form': formset.empty_form,
            'edit_mode': True,
            'plan': plan,
            'plan_info_fields': ['name','description','policy_type','scheme','underwriter'],
            'policy_fields': ['main_cover','main_premium','main_uw_cover','main_uw_premium','main_age_from','main_age_to','waiting_period','lapse_period'],
            'fee_fields': ['admin_fee','cash_payout','agent_commission','office_fee','scheme_fee','manager_fee','loyalty_programme','other_fees'],
            'other_fields': ['is_active'],
        })

    def post(self, request, pk):
        # Get the plan to update
        plan = get_object_or_404(Plan, pk=pk)
        
        # For rendering only
        form = PlanForm(request.POST, instance=plan)
        formset = PlanMemberTierFormSet(request.POST, instance=plan)
        
        try:
            # Get scheme
            scheme_id = request.POST.get('scheme')
            if scheme_id:
                scheme = Scheme.objects.get(pk=scheme_id)
                plan.scheme = scheme
            
            # Get other fields
            name = request.POST.get('name')
            if name:
                plan.name = name
            
            # Helper function to convert currency strings to Decimal
            from decimal import Decimal
            def safe_decimal(value, default=None):
                if value is None or value == '':
                    return default
                try:
                    # Remove any currency symbols and commas
                    cleaned = str(value).replace('R', '').replace(',', '')
                    return Decimal(cleaned or '0')
                except:
                    return default
            
            # Update text fields
            plan.description = request.POST.get('description', plan.description)
            plan.underwriter = request.POST.get('underwriter', plan.underwriter)
            plan.policy_type = request.POST.get('policy_type', plan.policy_type)
            
            # Update numeric fields (only if provided)
            premium = safe_decimal(request.POST.get('premium'), plan.premium)
            if premium is not None:
                plan.premium = premium
                
            main_cover = safe_decimal(request.POST.get('main_cover'), plan.main_cover)
            if main_cover is not None:
                plan.main_cover = main_cover
                
            main_premium = safe_decimal(request.POST.get('main_premium'), plan.main_premium)
            if main_premium is not None:
                plan.main_premium = main_premium
                
            # Update other fields if provided
            fields_to_update = [
                'min_age', 'max_age', 'main_uw_cover', 'main_uw_premium',
                'main_age_from', 'main_age_to', 'waiting_period', 'lapse_period',
                'max_dependents', 'admin_fee', 'cash_payout', 'agent_commission',
                'office_fee', 'scheme_fee', 'manager_fee', 'loyalty_programme',
                'other_fees', 'penalty_fee', 'service_fee'
            ]
            
            for field in fields_to_update:
                value = request.POST.get(field)
                if value not in (None, ''):
                    try:
                        if field in ['min_age', 'max_age', 'main_age_from', 'main_age_to', 
                                    'waiting_period', 'lapse_period', 'max_dependents']:
                            setattr(plan, field, int(value))
                        else:  # Decimal fields
                            setattr(plan, field, safe_decimal(value, getattr(plan, field)))
                    except:
                        pass  # Skip if conversion fails
            
            # Handle boolean fields
            is_active = request.POST.get('is_active')
            if is_active is not None:
                plan.is_active = is_active == 'on' or is_active == 'true' or is_active == True
            
            # Update timestamp
            plan.modified = timezone.now()
            
            # Save the plan
            plan.save()
            
            # Process member tiers if any (without validation)
            try:
                # Get the management form data
                total_forms = int(request.POST.get('form-TOTAL_FORMS', 0))
                
                # Reset member allowances
                plan.spouses_allowed = 0
                plan.children_allowed = 0
                plan.extended_allowed = 0
                
                # Process each form
                for i in range(total_forms):
                    # Check if this form has data and is not marked for deletion
                    prefix = f'form-{i}-'
                    user_type = request.POST.get(f'{prefix}user_type')
                    tier_id = request.POST.get(f'{prefix}id')
                    
                    # Get the allowed value from the hidden input
                    allowed_value = request.POST.get(f'allowed_{i}', '0')
                    
                    # Handle deletion
                    if request.POST.get(f'{prefix}DELETE') == 'on':
                        if tier_id:  # Only delete if it exists
                            PlanMemberTier.objects.filter(pk=tier_id).delete()
                        continue
                    
                    # Skip empty forms
                    if not user_type:
                        continue
                    
                    # Update member allowances based on user type
                    if user_type == 'Spouse':
                        plan.spouses_allowed = int(allowed_value or 0)
                    elif user_type == 'Child':
                        plan.children_allowed = int(allowed_value or 0)
                    elif user_type in ['Extended', 'Extended Child']:
                        plan.extended_allowed = int(allowed_value or 0)
                    
                    # Update existing or create new
                    if tier_id:
                        # Update existing tier
                        try:
                            tier = PlanMemberTier.objects.get(pk=tier_id)
                            tier.user_type = user_type
                            tier.age_from = int(request.POST.get(f'{prefix}age_from', 0) or 0)
                            tier.age_to = int(request.POST.get(f'{prefix}age_to', 100) or 100)
                            tier.cover = safe_decimal(request.POST.get(f'{prefix}cover'), tier.cover)
                            tier.premium = safe_decimal(request.POST.get(f'{prefix}premium'), tier.premium)
                            tier.underwriter_cover = safe_decimal(request.POST.get(f'{prefix}underwriter_cover'), tier.underwriter_cover)
                            tier.underwriter_premium = safe_decimal(request.POST.get(f'{prefix}underwriter_premium'), tier.underwriter_premium)
                            tier.save()
                        except PlanMemberTier.DoesNotExist:
                            pass  # Skip if tier doesn't exist
                    else:
                        # Create new tier
                        tier = PlanMemberTier(
                            plan=plan,
                            user_type=user_type,
                            age_from=int(request.POST.get(f'{prefix}age_from', 0) or 0),
                            age_to=int(request.POST.get(f'{prefix}age_to', 100) or 100),
                            cover=safe_decimal(request.POST.get(f'{prefix}cover'), Decimal('0')),
                            premium=safe_decimal(request.POST.get(f'{prefix}premium'), Decimal('0')),
                            underwriter_cover=safe_decimal(request.POST.get(f'{prefix}underwriter_cover'), Decimal('0')),
                            underwriter_premium=safe_decimal(request.POST.get(f'{prefix}underwriter_premium'), Decimal('0')),
                            extended_commission=Decimal('0')
                        )
                        tier.save()
                
                # Save plan again with updated allowances
                plan.save()
            except Exception as tier_error:
                # Log but continue - plan is already saved
                print(f"Error saving tiers: {tier_error}")
            
            messages.success(request, "Plan updated successfully.")
            return redirect('settings:plan')
            
        except Exception as e:
            messages.error(request, f"Error updating plan: {str(e)}")
        
        # If we get here, render the form again
        return self.get(request, pk)


@login_required
def plan_deactivate(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    plan.is_active = False
    plan.save()
    messages.success(request, "Plan deactivated.")
    return redirect('settings:plan')


@login_required
@transaction.atomic
def clone_plan(request, pk):
    original = get_object_or_404(Plan, pk=pk)
    base_name = f"{original.name} (Copy)"
    new_name = base_name
    counter = 1
    while Plan.objects.filter(name=new_name, scheme=original.scheme).exists():
        new_name = f"{base_name} {counter}"
        counter += 1

    new_plan = deepcopy(original)
    new_plan.pk = None
    new_plan.name = new_name
    new_plan.created = timezone.now()
    new_plan.modified = timezone.now()
    new_plan.is_active = True
    new_plan.save()

    for tier in original.tiers.all():
        new_tier = deepcopy(tier)
        new_tier.pk = None
        new_tier.plan = new_plan
        new_tier.save()

    messages.success(request, f"Plan '{original.name}' cloned successfully as '{new_plan.name}'.")
    return redirect('settings:plan_edit', pk=new_plan.pk)


@login_required
def export_plans_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plans.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Plan Name','Scheme','Underwriter','Main Premium','Main Cover',
        'Admin Fee','Waiting Period','Lapse Period','Spouses Allowed','Children Allowed','Extended Allowed','Is Active','Created'
    ])
    for plan in Plan.objects.select_related('scheme').all():
        writer.writerow([
            plan.name,
            plan.scheme.name if plan.scheme else '',
            plan.underwriter.name if plan.underwriter else '',
            plan.main_premium, plan.main_cover,
            plan.admin_fee, plan.waiting_period,
            plan.lapse_period, plan.spouses_allowed,
            plan.children_allowed, plan.extended_allowed,
            'Yes' if plan.is_active else 'No',
            plan.created.strftime('%Y-%m-%d'),
        ])
    return response


@login_required
def plan_template_download(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plan_template.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "name","description","policy_type","underwriter","main_cover","main_premium",
        "main_uw_cover","main_uw_premium","main_age_from","main_age_to",
        "admin_fee","cash_payout","agent_commission","office_fee",
        "scheme_fee","manager_fee","loyalty_programme","other_fees",
        "waiting_period","lapse_period","spouses_allowed","children_allowed","extended_allowed"
    ])
    return response


@login_required
def plan_import(request):
    import logging
    from django.db import transaction
    logger = logging.getLogger(__name__)
    errors = []
    warnings = []
    success_rows = []
    
    if request.method == 'POST':
        form = PlanImportForm(request.POST, request.FILES)
        if form.is_valid():
            scheme = form.cleaned_data['scheme']
            logger.info(f"Starting plan import for scheme: {scheme.name}")
            
            try:
                # Read and parse CSV file
                csv_file = request.FILES['file']
                if csv_file.size == 0:
                    messages.error(request, "The uploaded file is empty.")
                    return render(request, 'settings_app/plan_import.html', {'form': form})
                
                try:
                    data = csv_file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(data)
                    # Validate headers
                    required_headers = ['name', 'underwriter']
                    headers = reader.fieldnames if reader.fieldnames else []
                    missing_headers = [h for h in required_headers if h not in headers]
                    
                    if missing_headers:
                        messages.error(request, f"CSV file is missing required headers: {', '.join(missing_headers)}")
                        return render(request, 'settings_app/plan_import.html', {'form': form})
                        
                except Exception as e:
                    logger.exception(f"Error reading CSV: {e}")
                    messages.error(request, f"Could not read CSV file: {e}")
                    return render(request, 'settings_app/plan_import.html', {'form': form})
                
                # Process each row in the CSV
                created = 0
                for idx, row in enumerate(reader, start=2):
                    try:
                        # Validate required fields
                        plan_name = (row.get('name') or '').strip()
                        if not plan_name:
                            errors.append(f"Row {idx}: Missing plan name. Skipped.")
                            continue
                        
                        # Get or validate underwriter
                        uw_value = (row.get('underwriter') or '').strip()
                        if not uw_value:
                            warnings.append(f"Row {idx}: Missing underwriter for plan '{plan_name}'. Using empty value.")
                        
                        # Process policy_type
                        policy_type = (row.get('policy_type') or 'service').strip().lower()
                        if policy_type not in ['service', 'cash']:
                            warnings.append(f"Row {idx}: Invalid policy_type '{policy_type}' for plan '{plan_name}'. Using 'service'.")
                            policy_type = 'service'
                        
                        # Create or update the plan with transaction
                        with transaction.atomic():
                            plan, created_new = Plan.objects.update_or_create(
                                scheme=scheme,
                                name=plan_name,
                                defaults={
                                    'description':       row.get('description',''),
                                    'policy_type':      policy_type,
                                    'underwriter':      uw_value,
                                    'premium':          float(row.get('premium') or 0),
                                    'main_cover':       float(row.get('main_cover') or 0),
                                    'main_premium':     float(row.get('main_premium') or 0),
                                    'main_uw_cover':    float(row.get('main_uw_cover') or 0),
                                    'main_uw_premium':  float(row.get('main_uw_premium') or 0),
                                    'main_age_from':    int(row.get('main_age_from') or 0),
                                    'main_age_to':      int(row.get('main_age_to') or 0),
                                    'admin_fee':        float(row.get('admin_fee') or 0),
                                    'cash_payout':      float(row.get('cash_payout') or 0),
                                    'agent_commission': float(row.get('agent_commission') or 0),
                                    'office_fee':       float(row.get('office_fee') or 0),
                                    'scheme_fee':       float(row.get('scheme_fee') or 0),
                                    'manager_fee':      float(row.get('manager_fee') or 0),
                                    'loyalty_programme':float(row.get('loyalty_programme') or 0),
                                    'other_fees':       float(row.get('other_fees') or 0),
                                    'waiting_period':   int(row.get('waiting_period') or 0),
                                    'lapse_period':     int(row.get('lapse_period') or 0),
                                    'spouses_allowed':  int(row.get('spouses_allowed') or 0),
                                    'children_allowed': int(row.get('children_allowed') or 0),
                                    'extended_allowed': int(row.get('extended_allowed') or 0),
                                    'min_age':          int(row.get('min_age') or 0),
                                    'max_age':          int(row.get('max_age') or 0),
                                    'is_active':        True,
                                    'modified':         timezone.now().date(),
                                }
                            )
                            
                            action = "Created" if created_new else "Updated"
                            success_rows.append(f"Row {idx}: {action} plan '{plan_name}'")
                            created += 1
                            
                    except ValueError as ve:
                        # Handle numeric conversion errors
                        logger.error(f"Row {idx} value error: {ve}")
                        errors.append(f"Row {idx}: Invalid numeric value - {ve}")
                    except Exception as e:
                        # Handle any other errors
                        logger.exception(f"Row {idx} import error: {e}")
                        errors.append(f"Row {idx}: {e}")
                
                # Show appropriate messages based on results
                if created > 0:
                    messages.success(request, f"Successfully imported {created} plans.")
                    # Show first 5 success messages
                    for msg in success_rows[:5]:
                        messages.info(request, msg)
                    if len(success_rows) > 5:
                        messages.info(request, f"...and {len(success_rows) - 5} more plans processed successfully.")
                else:
                    messages.warning(request, "No plans were imported.")
                
                # Show warnings and errors
                for warning in warnings:
                    messages.warning(request, warning)
                    
                for error in errors:
                    messages.error(request, error)
                    
                if not created and not warnings and not errors:
                    messages.error(request, "No plans were imported and no errors were detected. Please check your CSV file format.")
                    
                return redirect('settings:plan')
                
            except Exception as e:
                logger.exception(f"Unexpected error during import: {e}")
                messages.error(request, f"Import failed: {e}")
    else:
        form = PlanImportForm()
        
    return render(request, 'settings_app/plan_import.html', {'form': form})


@login_required
def plan_delete(request, pk):
    try:
        plan = Plan.objects.get(pk=pk)
        plan.delete()
        messages.success(request, "Plan deleted successfully.")
    except Plan.DoesNotExist:
        messages.error(request, "That plan no longer exists.")
    return redirect('settings:plan')


# ─── Ajax Underwriter Fetch ───────────────────────────────────────────

@login_required
def get_underwriter_for_plan(request):
    plan_id = request.GET.get('plan_id')
    if not plan_id:
        return JsonResponse({'error': 'Missing plan_id'}, status=400)

    try:
        plan = Plan.objects.select_related('underwriter').get(pk=plan_id)
        return JsonResponse({'underwriter': plan.underwriter.name if plan.underwriter else ""})
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
