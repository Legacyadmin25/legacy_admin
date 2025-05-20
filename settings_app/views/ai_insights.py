import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from settings_app.models import Branch, UserRole
from schemes.models import Scheme
from settings_app.utils.openai_helper import get_branch_insights, get_scheme_insights

@login_required
@require_POST
def scheme_insights(request, pk):
    """
    AJAX view to get AI-generated insights about a scheme.
    Only available to internal_admin and scheme_manager roles.
    """
    # Get the scheme
    scheme = get_object_or_404(Scheme, pk=pk)
    
    # Check permissions
    user = request.user
    has_permission = False
    
    # Check if user has a role
    if hasattr(user, 'role'):
        role = user.role
        if role.role_type == 'internal_admin':
            has_permission = True
        elif role.role_type == 'scheme_manager' and role.scheme == scheme:
            has_permission = True
    
    if not has_permission:
        return JsonResponse({
            'error': 'You do not have permission to access AI insights for this scheme.'
        }, status=403)
    
    # Get the question from the request
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid request format.'
        }, status=400)
    
    if not question:
        return JsonResponse({
            'error': 'No question provided.'
        }, status=400)
    
    # Get insights
    insight = get_scheme_insights(scheme, question)
    
    return JsonResponse({
        'insight': insight
    })

@login_required
@require_POST
def branch_insights(request, pk):
    """
    AJAX view to get AI-generated insights about a branch.
    Only available to internal_admin and branch_owner roles.
    """
    # Get the branch
    branch = get_object_or_404(Branch, pk=pk)
    
    # Check permissions
    user = request.user
    has_permission = False
    
    # Check if user has a role
    if hasattr(user, 'role'):
        role = user.role
        if role.role_type == 'internal_admin':
            has_permission = True
        elif role.role_type == 'branch_owner' and role.branch == branch:
            has_permission = True
    
    if not has_permission:
        return JsonResponse({
            'error': 'You do not have permission to access AI insights for this branch.'
        }, status=403)
    
    # Get the question from the request
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid request format.'
        }, status=400)
    
    if not question:
        return JsonResponse({
            'error': 'No question provided.'
        }, status=400)
    
    # Get insights
    insight = get_branch_insights(branch, question)
    
    return JsonResponse({
        'insight': insight
    })
