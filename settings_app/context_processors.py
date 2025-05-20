# settings_app/context_processors.py (updated)
from django.contrib.auth.models import Group

def current_scheme(request):
    """
    Returns the current scheme and user permissions in context
    """
    context = {
        'scheme_name': '',
        'is_branch_owner': False,
        'is_scheme_admin': False,
        'user_schemes': []
    }
    
    if request.user.is_authenticated:
        # Get scheme from user profile
        profile = getattr(request.user, 'profile', None)
        scheme = getattr(profile, 'scheme', None) if profile else None
        context['scheme_name'] = scheme.name if scheme else ''
        
        # Check user groups
        context['is_branch_owner'] = request.user.groups.filter(name='Branch Owner').exists()
        context['is_scheme_admin'] = request.user.groups.filter(name='Scheme Admin').exists()
        
        # Get all schemes for the user
        if hasattr(request.user, 'scheme_set'):
            context['user_schemes'] = list(request.user.scheme_set.all())

    return context

def settings_context(request):
    from .models import Settings
    settings = Settings.load()
    return {'settings': settings}