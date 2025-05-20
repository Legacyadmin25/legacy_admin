import logging
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from payments.models import Payment, AIRequestLog

logger = logging.getLogger(__name__)

def get_payment_summary_for_member(member, user):
    """
    Generate an AI-powered summary of a member's payment history.
    
    Args:
        member: The Member model instance
        user: The User requesting the summary
        
    Returns:
        str: AI-generated summary or fallback message if AI is unavailable
    """
    try:
        # Get payments from the last 180 days
        start_date = timezone.now().date() - timedelta(days=180)
        recent_payments = Payment.objects.filter(
            member=member,
            date__gte=start_date,
            status='COMPLETED'
        ).order_by('-date')
        
        # If no payments, return fallback message
        if not recent_payments.exists():
            return "No recent payment data available."
        
        # Calculate statistics
        payment_count = recent_payments.count()
        avg_payment = recent_payments.aggregate(avg=Avg('amount'))['avg']
        last_payment = recent_payments.first()
        days_since_last = (timezone.now().date() - last_payment.date).days
        
        # Count payment methods
        payment_methods = recent_payments.values('payment_method').annotate(
            count=Count('payment_method')
        ).order_by('-count')
        most_common_method = payment_methods.first()['payment_method'] if payment_methods else "Unknown"
        
        # Prepare anonymized data for OpenAI - ensure POPIA compliance
        payment_data = {
            "payment_count": payment_count,
            "average_amount": float(avg_payment) if avg_payment else 0,
            "days_since_last_payment": days_since_last,
            "most_common_method": most_common_method,
            "payment_methods": [pm['payment_method'] for pm in payment_methods],
            "policy_status": member.policies.first().status if member.policies.exists() else "Unknown"
        }
        
        # Create prompt for OpenAI
        prompt = (
            "Summarize this funeral policy member's payment history in plain English. "
            "Include average amount, most common method, time since last payment."
        )
        
        # Try to get summary from OpenAI
        try:
            import openai
            from django.conf import settings
            
            # Check if OpenAI API key is configured
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OpenAI API key not configured")
                return generate_fallback_summary(payment_data)
                
            # Configure OpenAI
            openai.api_key = api_key
            
            # Make API call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes payment data for funeral policies."},
                    {"role": "user", "content": f"{prompt}\n\nData: {json.dumps(payment_data)}"}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            # Extract summary from response
            summary = response.choices[0].message.content.strip()
            
            # Log the AI request for compliance auditing
            AIRequestLog.objects.create(
                user=user,
                request_type='payment_summary',
                policy=member.policies.first() if member.policies.exists() else None,
                prompt_data=json.dumps(payment_data),
                response_data=summary
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            return generate_fallback_summary(payment_data)
            
    except Exception as e:
        logger.error(f"Error in get_payment_summary_for_member: {str(e)}")
        return "No recent payment data available."

def generate_fallback_summary(payment_data):
    """Generate a fallback summary when OpenAI is unavailable"""
    try:
        count = payment_data.get('payment_count', 0)
        avg = payment_data.get('average_amount', 0)
        days = payment_data.get('days_since_last_payment', 0)
        method = payment_data.get('most_common_method', 'Unknown')
        
        return (
            f"This member made {count} payments in the past 6 months. "
            f"Average payment is R{avg:.2f}. "
            f"They last paid via {method} {days} days ago."
        )
    except Exception as e:
        logger.error(f"Error generating fallback summary: {str(e)}")
        return "No recent payment data available."
