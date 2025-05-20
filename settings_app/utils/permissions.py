# settings_app/utils/permissions.py

def is_branch_owner(user):
    return user.groups.filter(name='Branch Owner').exists()

def is_scheme_admin(user):
    return user.groups.filter(name='Scheme Admin').exists()

def get_user_branch(user):
    return getattr(user.userprofile, 'branch', None)

def get_user_schemes(user):
    from settings_app.models import Scheme
    if user.is_superuser:
        return Scheme.objects.all()
    elif is_branch_owner(user):
        return Scheme.objects.filter(branch=get_user_branch(user))
    elif is_scheme_admin(user):
        return Scheme.objects.filter(admin_user=user)
    return Scheme.objects.none()
