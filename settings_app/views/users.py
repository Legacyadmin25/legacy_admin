from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from settings_app.models import UserProfile, Branch
from settings_app.forms import UserSetupForm
from django.http import HttpResponse
from io import TextIOWrapper
import csv
from django.contrib.auth.decorators import login_required  # <-- Add this import
from django.contrib.auth.models import Group  # <-- Add this import
from settings_app.models import UserImportLog  # <-- Add this import


# ─── User List View ────────────────────────────────────────────────────────
class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'settings_app/user_setup.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = UserSetupForm()
        return ctx


# ─── User Create View ───────────────────────────────────────────────────────
class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = UserSetupForm
    template_name = 'settings_app/user_setup.html'
    success_url = reverse_lazy('settings:user_setup')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['editing'] = False
        return ctx


# ─── User Update View ───────────────────────────────────────────────────────
class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserSetupForm
    template_name = 'settings_app/user_setup.html'
    success_url = reverse_lazy('settings:user_setup')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['editing'] = True
        return ctx


# ─── User Delete View ───────────────────────────────────────────────────────
class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'settings_app/user_confirm_delete.html'
    success_url = reverse_lazy('settings:user_setup')


# ─── User Import Logic ───────────────────────────────────────────────────────
@login_required
def import_users_view(request):
    if not request.user.is_superuser and not request.user.groups.filter(name="Administrator").exists():
        return HttpResponse("Access Denied: You do not have permission to import users.", status=403)

    context = {'errors': [], 'success': 0}
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded = TextIOWrapper(csv_file.file, encoding='utf-8')
        reader = csv.DictReader(decoded)

        for row_num, row in enumerate(reader, start=2):
            try:
                username = row['username'].strip().lower()
                email = row.get('email', '').strip().lower()

                if not username:
                    context['errors'].append(f"Row {row_num}: Missing username.")
                    continue
                if User.objects.filter(username=username).exists():
                    context['errors'].append(f"Row {row_num}: Username '{username}' already exists.")
                    continue
                if email and User.objects.filter(email=email).exists():
                    context['errors'].append(f"Row {row_num}: Email '{email}' already exists.")
                    continue

                user = User(
                    username=username,
                    first_name=row.get('first_name', '').strip(),
                    last_name=row.get('last_name', '').strip(),
                    email=email,
                    is_active=row.get('is_active', 'True').strip().lower() in ['1', 'true', 'yes']
                )
                password = row.get('password', '').strip()
                if password:
                    user.set_password(password)
                user.save()

                # Groups
                group_names = [g.strip() for g in row.get('groups', '').split(',') if g.strip()]
                for group_name in group_names:
                    group, _ = Group.objects.get_or_create(name=group_name)
                    user.groups.add(group)

                # Branch and profile
                branch_name = row.get('branch_name', '').strip()
                branch = Branch.objects.filter(name__iexact=branch_name).first()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.branch           = branch
                profile.id_number        = row.get('id_number', '').strip()
                profile.cell_no          = row.get('cell_no', '').strip()
                profile.physical_address = row.get('physical_address', '').strip()
                profile.street           = row.get('street', '').strip()
                profile.town             = row.get('town', '').strip()
                profile.province         = row.get('province', '').strip()
                profile.code             = row.get('code', '').strip()
                profile.save()

                context['success'] += 1

            except Exception as e:
                context['errors'].append(f"Row {row_num}: {str(e)}")

        # Log the import
        UserImportLog.objects.create(
            uploaded_by=request.user,
            success_count=context['success'],
            error_count=len(context['errors']),
            error_log="\n".join(context['errors']) if context['errors'] else ''
        )

    return render(request, 'settings_app/user_import.html', context)


# ─── User Import Template Download ──────────────────────────────────────────
@login_required
def user_template_download(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_import_template.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'first_name', 'last_name', 'username', 'email', 'password', 'is_active',
        'id_number', 'cell_no', 'physical_address', 'street', 'town', 'province', 'code',
        'branch_name', 'groups'
    ])
    return response
