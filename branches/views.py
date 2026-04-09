from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .forms import BranchForm
from .models import Branch
from schemes.models import Scheme
from config.permissions import can_view_branch, get_user_accessible_branches, user_has_role


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
    
    return render(request, 'branches/branch_detail.html', {'branch': branch})


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
