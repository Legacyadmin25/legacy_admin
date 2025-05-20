from django.shortcuts import render, redirect  # <-- Added the redirect import
from django.contrib import messages
from django.contrib.auth.models import Group
from settings_app.forms import GroupSelectForm
from settings_app.models import PagePermission
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse  # <-- Added the HttpResponse import
import csv  # <-- Added the csv import

# ─── Manage Permissions View ────────────────────────────────────────────────
@login_required
def manage_rights_view(request):
    form = GroupSelectForm(request.POST or None)
    selected_group = None
    pages = []

    if request.method == 'POST' and form.is_valid():
        selected_group = form.cleaned_data['group']
        pages = PagePermission.objects.filter(group=selected_group)

        # Save permissions
        if any(k.startswith('has_rights_') for k in request.POST):
            for page in pages:
                page_id = str(page.id)
                page.has_rights = f'has_rights_{page_id}' in request.POST
                page.is_read = f'is_read_{page_id}' in request.POST
                page.is_write = f'is_write_{page_id}' in request.POST
                page.is_delete = f'is_delete_{page_id}' in request.POST
                page.is_update = f'is_update_{page_id}' in request.POST
                page.is_payment_reversal = f'is_payment_reversal_{page_id}' in request.POST
                page.save()

            messages.success(request, "Permissions updated successfully.")

    return render(request, 'settings_app/manage_rights.html', {
        'form': form,
        'selected_group': selected_group,
        'pages': pages,
    })


# ─── Permissions Export View ────────────────────────────────────────────────
@login_required
def export_permissions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="permissions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Group', 'Page', 'Has Rights', 'Read', 'Write', 'Update', 'Delete', 'Payment Reversal'
    ])

    permissions = PagePermission.objects.all()
    for permission in permissions:
        writer.writerow([
            permission.group.name,
            permission.page_name,
            'Yes' if permission.has_rights else 'No',
            'Yes' if permission.is_read else 'No',
            'Yes' if permission.is_write else 'No',
            'Yes' if permission.is_update else 'No',
            'Yes' if permission.is_delete else 'No',
            'Yes' if permission.is_payment_reversal else 'No',
        ])

    return response


# ─── Group Permissions Management ──────────────────────────────────────────
@login_required
def group_permissions(request, group_id):
    group = Group.objects.get(pk=group_id)
    permissions = PagePermission.objects.filter(group=group)

    if request.method == 'POST':
        for perm in permissions:
            perm.has_rights = 'has_rights_{}'.format(perm.id) in request.POST
            perm.is_read = 'is_read_{}'.format(perm.id) in request.POST
            perm.is_write = 'is_write_{}'.format(perm.id) in request.POST
            perm.is_update = 'is_update_{}'.format(perm.id) in request.POST
            perm.is_delete = 'is_delete_{}'.format(perm.id) in request.POST
            perm.is_payment_reversal = 'is_payment_reversal_{}'.format(perm.id) in request.POST
            perm.save()

        messages.success(request, f"Permissions for group '{group.name}' updated successfully.")
        return redirect('settings:manage_rights')

    return render(request, 'settings_app/group_permissions.html', {
        'group': group,
        'permissions': permissions
    })
