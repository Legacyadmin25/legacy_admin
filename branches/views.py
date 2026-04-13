from datetime import timedelta

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .forms import BranchForm
from .models import Branch
from schemes.models import Scheme
from config.permissions import can_view_branch, get_user_accessible_branches, user_has_role


def _scheme_self_onboarding_enabled():
    return settings.FEATURE_FLAGS.get('SCHEME_SELF_ONBOARDING', False)


@login_required
def branch_setup(request):
    from .models import Bank
    
    # Ensure we have at least one bank
    if not Bank.objects.exists():
        # Create default banks if none exist
        default_banks = [
            ("ABSA", "632005"),
            ("FNB", "250655"),
            ("Nedbank", "198765"),
            ("Standard Bank", "051001"),
            ("Capitec Bank", "470010"),
        ]
        for name, branch_code in default_banks:
            Bank.objects.get_or_create(
                name=name,
                defaults={'branch_code': branch_code}
            )
    
    # Check permission - only superuser or branch managers
    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied("You do not have permission to setup branches.")
    
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            # Ensure the bank relationship is set
            branch = form.save(commit=False)
            bank_id = request.POST.get('bank')
            if bank_id:
                try:
                    bank = Bank.objects.get(id=bank_id)
                    branch.bank = bank
                    branch.save()
                    form.save_m2m()  # Save any many-to-many relationships
                    return redirect('branches:branch_setup')
                except Bank.DoesNotExist:
                    form.add_error('bank', 'Selected bank does not exist')
    else:
        form = BranchForm()

    # Filter branches based on user scope
    branches = get_user_accessible_branches(request.user).order_by('-modified_date')
    banks = Bank.objects.all()
    
    return render(request, 'branches/branch_setup.html', {
        'form': form,
        'branches': branches,
        'banks': banks,
    })


@login_required
def branch_edit(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    
    # Check permission
    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied("You do not have permission to edit branches.")
    
    # Check if user can access this specific branch
    if not can_view_branch(request.user, branch):
        raise PermissionDenied("You do not have permission to edit this branch.")
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            return redirect('branches:branch_setup')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'branches/edit_branch.html', {'form': form, 'branch': branch})


@login_required
def branch_list(request):
    # Check permission
    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied("You do not have permission to view branches.")
    
    # Filter branches based on user scope
    branches = get_user_accessible_branches(request.user).order_by('-modified_date')
    return render(request, 'branches/branch_list.html', {'branches': branches})


@login_required
def branch_detail(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    
    # Check permission
    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied("You do not have permission to view branches.")
    
    # Check if user can access this specific branch
    if not can_view_branch(request.user, branch):
        raise PermissionDenied("You do not have permission to view this branch.")

    context = {'branch': branch, 'scheme_self_onboarding_enabled': _scheme_self_onboarding_enabled()}

    if context['scheme_self_onboarding_enabled']:
        from schemes.onboarding.models import BranchSchemeOnboarding

        context['onboarding_links'] = BranchSchemeOnboarding.objects.filter(branch=branch).order_by('-created_at')[:10]

    return render(request, 'branches/branch_detail.html', context)


@login_required
def branch_create_scheme_onboarding_link(request, branch_id):
    if request.method != 'POST':
        raise PermissionDenied('Invalid request method.')

    if not _scheme_self_onboarding_enabled():
        raise PermissionDenied('Scheme self-onboarding is currently disabled.')

    branch = get_object_or_404(Branch, id=branch_id)

    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied('You do not have permission to create onboarding links.')

    if not can_view_branch(request.user, branch):
        raise PermissionDenied('You do not have permission to manage this branch.')

    from schemes.onboarding.models import BranchSchemeOnboarding

    try:
        expires_days = int(request.POST.get('expires_days', '7'))
    except ValueError:
        expires_days = 7

    expires_days = max(1, min(expires_days, 90))
    expires_at = timezone.now() + timedelta(days=expires_days)
    onboarding = BranchSchemeOnboarding.create_with_token(branch=branch, expires_at=expires_at)

    site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
    if site_url:
        onboarding_url = f"{site_url}/scheme-onboarding/start/{onboarding.onboarding_token}/"
    else:
        onboarding_url = request.build_absolute_uri(
            f"/scheme-onboarding/start/{onboarding.onboarding_token}/"
        )

    request.session['latest_scheme_onboarding_link'] = onboarding_url
    messages.success(request, f'Scheme onboarding link created. Expires in {expires_days} day(s).')
    return redirect('branches:branch_detail', branch_id=branch.id)


@login_required
def branch_delete(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    
    # Check permission
    if not (request.user.is_superuser or user_has_role(request.user, 'Branch Owner', 'Administrator')):
        raise PermissionDenied("You do not have permission to delete branches.")
    
    # Check if user can access this specific branch
    if not can_view_branch(request.user, branch):
        raise PermissionDenied("You do not have permission to delete this branch.")
    
    if request.method == 'POST':
        branch.delete()
        return redirect('branches:branch_list')
    return render(request, 'branches/delete_branch.html', {'branch': branch})
