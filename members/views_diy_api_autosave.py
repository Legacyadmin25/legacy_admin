from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required

import json
import decimal

from settings_app.models import Agent
from schemes.models import Scheme, Plan
from .models_incomplete import IncompleteApplication


@require_GET
def get_plans(request):
    """Get available plans for a scheme"""
    scheme_id = request.GET.get('scheme_id')
    if not scheme_id:
        return JsonResponse({'error': 'Scheme ID is required'}, status=400)
    
    try:
        scheme = Scheme.objects.get(id=scheme_id)
        plans = []
        
        for plan in scheme.plans.all():
            plans.append({
                'id': plan.id,
                'name': plan.name,
                'description': plan.description,
                'base_premium': float(plan.base_premium),
                'features': [
                    f"Cover up to R{int(plan.max_cover_amount):,}",
                    f"Includes {plan.included_benefits}",
                    f"Waiting period: {plan.waiting_period} days"
                ]
            })
        
        return JsonResponse({'plans': plans})
    except Scheme.DoesNotExist:
        return JsonResponse({'error': 'Scheme not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@ensure_csrf_cookie
def calculate_premium(request):
    """Calculate premium based on selected plan and options"""
    try:
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        cover_amount = data.get('cover_amount', 10000)
        has_spouse = data.get('has_spouse', False)
        has_children = data.get('has_children', False)
        children_count = data.get('children_count', 0)
        has_extended_family = data.get('has_extended_family', False)
        extended_family_count = data.get('extended_family_count', 0)
        
        if not plan_id:
            return JsonResponse({'error': 'Plan ID is required'}, status=400)
        
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return JsonResponse({'error': 'Plan not found'}, status=404)
        
        # Base premium calculation
        base_premium = plan.base_premium
        
        # Cover amount adjustment
        cover_factor = decimal.Decimal(cover_amount) / decimal.Decimal(10000)  # Base cover is 10,000
        premium = base_premium * cover_factor
        
        # Add spouse premium
        if has_spouse:
            premium += premium * decimal.Decimal('0.5')  # 50% of main member premium
        
        # Add children premium
        if has_children and children_count > 0:
            child_premium = premium * decimal.Decimal('0.2')  # 20% of main member premium per child
            premium += child_premium * decimal.Decimal(min(children_count, 10))  # Max 10 children
        
        # Add extended family premium
        if has_extended_family and extended_family_count > 0:
            extended_premium = premium * decimal.Decimal('0.3')  # 30% of main member premium per extended family member
            premium += extended_premium * decimal.Decimal(min(extended_family_count, 10))  # Max 10 extended family members
        
        # Round to 2 decimal places
        premium = round(premium, 2)
        
        # Save plan name for display in review step
        plan_name = plan.name
        
        return JsonResponse({
            'premium': float(premium),
            'plan_name': plan_name,
            'cover_amount': cover_amount
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@login_required
def get_application_stats(request):
    """Get statistics for incomplete applications"""
    user = request.user
    
    # Check if user is an agent
    try:
        agent = user.agent
        incomplete_count = IncompleteApplication.objects.filter(agent=agent, status__in=['draft', 'in_progress']).count()
        abandoned_count = IncompleteApplication.objects.filter(agent=agent, status='abandoned').count()
        completed_count = IncompleteApplication.objects.filter(agent=agent, status='completed').count()
    except:
        # For branch owners, scheme managers, and internal admins
        role = getattr(user, 'role', None)
        if role:
            if role.role_type == 'branch_owner':
                branch = role.branch
                incomplete_count = IncompleteApplication.objects.filter(branch=branch, status__in=['draft', 'in_progress']).count()
                abandoned_count = IncompleteApplication.objects.filter(branch=branch, status='abandoned').count()
                completed_count = IncompleteApplication.objects.filter(branch=branch, status='completed').count()
            elif role.role_type == 'scheme_manager':
                scheme = role.scheme
                incomplete_count = IncompleteApplication.objects.filter(scheme=scheme, status__in=['draft', 'in_progress']).count()
                abandoned_count = IncompleteApplication.objects.filter(scheme=scheme, status='abandoned').count()
                completed_count = IncompleteApplication.objects.filter(scheme=scheme, status='completed').count()
            elif role.role_type == 'internal_admin':
                incomplete_count = IncompleteApplication.objects.filter(status__in=['draft', 'in_progress']).count()
                abandoned_count = IncompleteApplication.objects.filter(status='abandoned').count()
                completed_count = IncompleteApplication.objects.filter(status='completed').count()
            else:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
        else:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    return JsonResponse({
        'incomplete_count': incomplete_count,
        'abandoned_count': abandoned_count,
        'completed_count': completed_count,
        'total_count': incomplete_count + abandoned_count + completed_count
    })
