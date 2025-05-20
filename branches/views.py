from django.shortcuts import render, redirect
from .forms import BranchForm
from .models import Branch
from django.shortcuts import render, get_object_or_404

def branch_setup(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('branches:branch_setup')
    else:
        form = BranchForm()

    branches = Branch.objects.all().order_by('-modified_date')
    return render(request, 'branches/branch_setup.html', {
        'form': form,
        'branches': branches,
    })

from django.shortcuts import render, redirect, get_object_or_404
from .forms import BranchForm
from .models import Branch
from schemes.models import Scheme

def branch_edit(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            return redirect('branches:branch_setup')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'branches/edit_branch.html', {'form': form, 'branch': branch})

def branch_list(request):
    branches = Branch.objects.all().order_by('-modified_date')
    return render(request, 'branches/branch_list.html', {'branches': branches})

def branch_detail(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    return render(request, 'branches/branch_detail.html', {'branch': branch})

def branch_delete(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        branch.delete()
        return redirect('branches:branch_list')
    return render(request, 'branches/delete_branch.html', {'branch': branch})
