from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Max, Min
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import Policy, Dependent, Beneficiary
from payments.models import Payment
from .forms import (
    PersonalDetailsEditForm, 
    AddressEditForm, 
    PolicyEditForm, 
    DependentForm,
    BeneficiaryForm,
    PaymentOptionsEditForm,
    CommunicationForm,
    NotesForm
)

@login_required
def policy_detail(request, policy_id):
    """
    Main policy detail view that handles all tabs and their forms
    """
    policy = get_object_or_404(Policy.objects.select_related('member', 'plan__scheme'), id=policy_id)
    active_tab = request.GET.get('tab', 'personal')
    
    # Check permissions
    if not request.user.is_superuser:
        # For non-superusers, check if they have access to this policy
        if request.user.groups.filter(name="Branch Owner").exists():
            if policy.plan.scheme.branch != request.user.userprofile.branch:
                messages.error(request, "You don't have permission to view this policy.")
                return redirect('members:find_policy')
        elif request.user.groups.filter(name="Scheme Admin").exists():
            if policy.plan.scheme.admin_user != request.user:
                messages.error(request, "You don't have permission to view this policy.")
                return redirect('members:find_policy')
        elif policy.member.user != request.user:
            messages.error(request, "You don't have permission to view this policy.")
            return redirect('members:find_policy')
    
    # Initialize forms
    personal_form = PersonalDetailsEditForm(instance=policy.member, prefix='personal')
    address_form = AddressEditForm(instance=policy.member, prefix='address')
    policy_form = PolicyEditForm(instance=policy, prefix='policy')
    payment_form = PaymentOptionsEditForm(instance=policy, prefix='payment')
    communication_form = CommunicationForm(prefix='comm')
    notes_form = NotesForm(prefix='notes')
    
    # Handle form submissions
    if request.method == 'POST':
        if 'save_personal' in request.POST:
            personal_form = PersonalDetailsEditForm(
                request.POST, 
                instance=policy.member, 
                prefix='personal'
            )
            if personal_form.is_valid():
                personal_form.save()
                messages.success(request, 'Personal details updated successfully.')
                return redirect(f"{reverse('members:policy_detail', args=[policy.id])}?tab=personal")
            active_tab = 'personal'
            
        elif 'save_address' in request.POST:
            address_form = AddressEditForm(
                request.POST, 
                instance=policy.member, 
                prefix='address'
            )
            if address_form.is_valid():
                address_form.save()
                messages.success(request, 'Address details updated successfully.')
                return redirect(f"{reverse('members:policy_detail', args=[policy.id])}?tab=address")
            active_tab = 'address'
            
        elif 'save_policy' in request.POST:
            policy_form = PolicyEditForm(
                request.POST, 
                instance=policy, 
                prefix='policy'
            )
            if policy_form.is_valid():
                policy_form.save()
                messages.success(request, 'Policy details updated successfully.')
                return redirect(f"{reverse('members:policy_detail', args=[policy.id])}?tab=policy")
            active_tab = 'policy'
            
        elif 'save_payment' in request.POST:
            payment_form = PaymentOptionsEditForm(
                request.POST, 
                instance=policy, 
                prefix='payment'
            )
            if payment_form.is_valid():
                payment_form.save()
                messages.success(request, 'Payment details updated successfully.')
                return redirect(f"{reverse('members:policy_detail', args=[policy.id])}?tab=payment")
            active_tab = 'payment'
    
    # Get dependents and beneficiaries
    dependents = policy.dependents.all()
    beneficiaries = policy.beneficiaries.all()
    
    # Calculate payment statistics for the payment summary tab
    payment_stats = None
    if active_tab == 'payment':
        payment_stats = calculate_payment_statistics(policy)
        
        # Check if the policy is at risk of lapsing
        policy.check_lapse_risk()
    
    # Initialize context with policy and active tab
    context = {
        'policy': policy,
        'active_tab': active_tab,
        'personal_form': personal_form,
        'address_form': address_form,
        'policy_form': policy_form,
        'payment_form': payment_form,
        'communication_form': communication_form,
        'notes_form': notes_form,
        'payment_stats': payment_stats,
        'dependents': dependents,
        'beneficiaries': beneficiaries,
        'is_superuser': request.user.is_superuser,
        'is_branch_owner': request.user.groups.filter(name="Branch Owner").exists(),
        'is_scheme_admin': request.user.groups.filter(name="Scheme Admin").exists(),
    }
    
    return render(request, 'members/find_policy/detail.html', context)

@login_required
@require_http_methods(["POST"])
def add_dependent(request, policy_id):
    """
    Handle adding a new dependent via AJAX
    """
    policy = get_object_or_404(Policy, id=policy_id)
    
    # Check permissions
    if not request.user.is_superuser and policy.member.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    form = DependentForm(request.POST, policy=policy)
    if form.is_valid():
        dependent = form.save(commit=False)
        dependent.policy = policy
        dependent.save()
        return JsonResponse({
            'success': True,
            'id': dependent.id,
            'full_name': dependent.full_name,
            'id_number': dependent.id_number,
            'relationship': dependent.get_relationship_display(),
            'date_of_birth': dependent.date_of_birth.strftime('%Y-%m-%d') if dependent.date_of_birth else ''
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)

@login_required
@require_http_methods(["POST"])
def add_beneficiary(request, policy_id):
    """
    Handle adding a new beneficiary via AJAX
    """
    policy = get_object_or_404(Policy, id=policy_id)
    
    # Check permissions
    if not request.user.is_superuser and policy.member.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    form = BeneficiaryForm(request.POST, policy=policy)
    if form.is_valid():
        beneficiary = form.save(commit=False)
        beneficiary.policy = policy
        beneficiary.save()
        return JsonResponse({
            'success': True,
            'id': beneficiary.id,
            'full_name': beneficiary.full_name,
            'id_number': beneficiary.id_number,
            'relationship': beneficiary.get_relationship_display(),
            'percentage': float(beneficiary.percentage)
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)

@login_required
def delete_dependent(request, policy_id, dep_id):
    """
    Handle deleting a dependent
    """
    policy = get_object_or_404(Policy, id=policy_id)
    dependent = get_object_or_404(Dependent, id=dep_id, policy=policy)
    
    # Check permissions
    if not request.user.is_superuser and policy.member.user != request.user:
        messages.error(request, 'You do not have permission to delete this dependent.')
    else:
        dependent.delete()
        messages.success(request, 'Dependent deleted successfully.')
    
    return redirect(f"{reverse('members:policy_detail', args=[policy.id])}?tab=dependents")

@login_required
def delete_beneficiary(request, policy_id, ben_id):
    """
    Handle deleting a beneficiary
    """
    policy = get_object_or_404(Policy, id=policy_id)
    beneficiary = get_object_or_404(Beneficiary, id=ben_id, policy=policy)
    
    # Check permissions
    if not request.user.is_superuser and policy.member.user != request.user:
        messages.error(request, "You don't have permission to delete this beneficiary.")
        return redirect('members:policy_detail', policy_id=policy_id)
    
    beneficiary.delete()
    messages.success(request, f"Beneficiary {beneficiary.first_name} {beneficiary.last_name} has been deleted.")
    
    return redirect('members:policy_detail', policy_id=policy_id)


def calculate_payment_statistics(policy):
    """
    Calculate payment statistics for a policy.
    Returns a dictionary with various payment statistics.
    """
    payments = Payment.objects.filter(policy=policy)
    
    # Basic statistics
    total_paid = payments.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    avg_payment = payments.filter(status='successful').aggregate(Avg('amount'))['amount__avg'] or 0
    
    # Most used payment method
    payment_methods = payments.filter(status='successful').values('payment_method').annotate(
        count=Count('payment_method')).order_by('-count')
    most_used_method = payment_methods[0]['payment_method'] if payment_methods else "N/A"
    
    # Last payment date
    last_payment = payments.filter(status='successful').order_by('-date').first()
    last_payment_date = last_payment.date.strftime('%d %b %Y') if last_payment else "N/A"
    
    # Calculate payment gaps
    payment_dates = list(payments.filter(status='successful').order_by('date').values_list('date', flat=True))
    longest_gap = 0
    
    if len(payment_dates) > 1:
        gaps = []
        for i in range(1, len(payment_dates)):
            gap = (payment_dates[i] - payment_dates[i-1]).days
            gaps.append(gap)
        longest_gap = max(gaps) if gaps else 0
    
    # Generate monthly payment data for the last 12 months
    monthly_payments = []
    today = timezone.now().date()
    
    for i in range(12, 0, -1):
        month_start = (today - relativedelta(months=i)).replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
        
        month_payments = payments.filter(
            date__gte=month_start,
            date__lte=month_end,
            status='successful'
        )
        
        month_total = month_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_payments.append({
            'month': month_start.strftime('%b %Y'),
            'amount': float(month_total)
        })
    
    return {
        'total_paid': float(total_paid),
        'avg_payment': float(avg_payment),
        'most_used_method': most_used_method,
        'last_payment_date': last_payment_date,
        'longest_gap': longest_gap,
        'monthly_payments': monthly_payments
    }
