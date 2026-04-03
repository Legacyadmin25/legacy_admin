"""
DIY Signup views - redirects to the appropriate implementation
This is a compatibility shim to avoid import errors while we refactor.
"""

try:
    # Try importing from the steps implementation
    from .views_diy_steps import diy_signup_start
except ImportError:
    try:
        # Fallback to the base implementation
        from .views_diy_base import diy_signup_start
    except ImportError:
        # If neither works, provide a placeholder
        from django.shortcuts import render
        
        def diy_signup_start(request, token=None):
            """Placeholder DIY signup start - needs proper implementation"""
            return render(request, 'members/diy_placeholder.html', {
                'error': 'DIY signup module not properly configured',
            })

__all__ = ['diy_signup_start']
