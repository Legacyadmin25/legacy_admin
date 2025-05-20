import json
import os
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count, Max, Min
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import Policy
from payments.models import Payment, AIRequestLog

# Check if OpenAI API key is set
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
USE_OPENAI = OPENAI_API_KEY is not None

# Try to import OpenAI if available
try:
    import openai
    if USE_OPENAI:
        openai.api_key = OPENAI_API_KEY
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

@login_required
def get_payment_ai_summary(request, policy_id):
    """
    Generate an AI summary of payment history for a policy.
    Only accessible to internal_admin and scheme_manager roles.
    """
    # Check user permissions
    if request.user.role.role_type not in ['internal_admin', 'scheme_manager']:
        return JsonResponse({
            'error': 'Permission denied. Only administrators can view AI summaries.'
        }, status=403)
    
    policy = get_object_or_404(Policy, id=policy_id)
    
    # Check if we have enough payment data to generate a summary
    payments = Payment.objects.filter(policy=policy).order_by('-date')
    if payments.count() < 3:
        return JsonResponse({
            'summary': "Not enough payment history to generate a meaningful summary."
        })
    
    # Calculate payment statistics
    payment_stats = calculate_payment_statistics(policy)
    
    # Generate AI summary if OpenAI is available
    if USE_OPENAI and OPENAI_AVAILABLE:
        summary = generate_openai_summary(policy, payment_stats)
        
        # Log the AI request
        AIRequestLog.objects.create(
            user=request.user,
            request_type='payment_summary',
            policy=policy,
            prompt_data=json.dumps(payment_stats),
            response_data=summary
        )
    else:
        # Generate a rule-based summary if OpenAI is not available
        summary = generate_rule_based_summary(policy, payment_stats)
    
    return JsonResponse({
        'summary': summary,
        'stats': payment_stats
    })

def calculate_payment_statistics(policy):
    """Calculate payment statistics for a policy."""
    payments = Payment.objects.filter(policy=policy)
    
    # Basic statistics
    total_paid = payments.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    avg_payment = payments.filter(status='successful').aggregate(Avg('amount'))['amount__sum'] or 0
    
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
    
    # Check if policy is at risk of lapsing
    days_since_last_payment = 0
    if last_payment:
        days_since_last_payment = (timezone.now().date() - last_payment.date).days
    
    lapse_risk = "None"
    if days_since_last_payment > 60:
        lapse_risk = "High"
    elif days_since_last_payment > 30:
        lapse_risk = "Medium"
    elif days_since_last_payment > 15:
        lapse_risk = "Low"
    
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
        'days_since_last_payment': days_since_last_payment,
        'lapse_risk': lapse_risk,
        'monthly_payments': monthly_payments
    }

def generate_openai_summary(policy, payment_stats):
    """Generate an AI summary using OpenAI."""
    try:
        # Anonymize the data for the prompt
        policy_number = f"POLICY-{policy.id}"
        
        # Create a prompt with anonymized data
        prompt = f"""
        Generate a concise summary (3-4 sentences) of the following payment history for policy {policy_number}:
        
        - Total paid to date: R{payment_stats['total_paid']}
        - Average payment: R{payment_stats['avg_payment']}
        - Most used payment method: {payment_stats['most_used_method']}
        - Last payment date: {payment_stats['last_payment_date']}
        - Longest gap between payments: {payment_stats['longest_gap']} days
        - Days since last payment: {payment_stats['days_since_last_payment']}
        - Lapse risk: {payment_stats['lapse_risk']}
        
        Monthly payment amounts for the last 12 months:
        {', '.join([f"{m['month']}: R{m['amount']}" for m in payment_stats['monthly_payments']])}
        
        Focus on payment patterns, consistency, and any risk of policy lapse. Do not include any personal information.
        """
        
        # Call OpenAI API
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        
        summary = response.choices[0].text.strip()
        return summary
    
    except Exception as e:
        # Fallback to rule-based summary if OpenAI fails
        return generate_rule_based_summary(policy, payment_stats)

def generate_rule_based_summary(policy, payment_stats):
    """Generate a rule-based summary when OpenAI is not available."""
    summary_parts = []
    
    # Payment consistency
    if payment_stats['longest_gap'] > 60:
        summary_parts.append(f"This policy has experienced significant payment gaps (up to {payment_stats['longest_gap']} days).")
    elif payment_stats['longest_gap'] > 30:
        summary_parts.append(f"This policy has had moderate payment gaps (up to {payment_stats['longest_gap']} days).")
    else:
        summary_parts.append("This policy has maintained consistent payment intervals.")
    
    # Recent payment activity
    if payment_stats['days_since_last_payment'] > 45:
        summary_parts.append(f"The last payment was {payment_stats['days_since_last_payment']} days ago, which is concerning.")
    elif payment_stats['days_since_last_payment'] > 30:
        summary_parts.append(f"The last payment was {payment_stats['days_since_last_payment']} days ago, which requires attention.")
    else:
        summary_parts.append(f"The most recent payment was {payment_stats['days_since_last_payment']} days ago.")
    
    # Payment method
    summary_parts.append(f"The primary payment method used is {payment_stats['most_used_method']}.")
    
    # Lapse risk
    if payment_stats['lapse_risk'] == "High":
        summary_parts.append("This policy is at high risk of lapsing and requires immediate attention.")
    elif payment_stats['lapse_risk'] == "Medium":
        summary_parts.append("This policy has a moderate risk of lapsing and should be monitored.")
    elif payment_stats['lapse_risk'] == "Low":
        summary_parts.append("This policy has a low risk of lapsing but should still be monitored.")
    else:
        summary_parts.append("This policy shows no current risk of lapsing.")
    
    return " ".join(summary_parts)
