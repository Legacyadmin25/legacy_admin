from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# ─── General Views ───────────────────────────────────────────────────────────
@login_required
def general_settings(request):
    return render(request, 'settings_app/general_settings.html')

