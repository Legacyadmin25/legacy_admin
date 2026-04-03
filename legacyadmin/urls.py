from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from dashboard.views import index as dashboard_home
from .health import health_check, readiness_probe, liveness_probe
from .metrics import metrics_view

urlpatterns = [
    # Health checks and monitoring
    path('health/', health_check, name='health_check'),
    path('health/readiness/', readiness_probe, name='readiness_probe'),
    path('health/liveness/', liveness_probe, name='liveness_probe'),
    path('metrics/', metrics_view, name='metrics'),
    
    # Admin
    path('admin/', admin.site.urls),

    # Root → dashboard (Ensure the home URL is linked to the index view)
    path('', dashboard_home, name='index'),
    
    # Authentication - Using custom accounts app
    path('accounts/', include('accounts.urls', namespace='accounts')),
    # Django built-in auth URLs (login, logout, password_change, etc.)
    path('accounts/', include('django.contrib.auth.urls')),

    # Dashboard
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),

    # AI Reports
    path('reports/ai/', include(('reports_ai.urls', 'reports_ai'), namespace='reports_ai')),

    # Public Enrollment (No auth required)
    path('apply/', include(('members.urls_public_enrollment', 'public_enrollment'), namespace='public_enrollment')),
    
    # Admin - Application Management (use app_admin to avoid namespace conflict with Django admin)
    path('admin/applications/', include(('members.urls_admin', 'app_admin'), namespace='app_admin')),
    
    # Other apps
    path('settings/', include(('settings_app.urls', 'settings'), namespace='settings')),
    path('members/', include(('members.urls', 'members'), namespace='members')),
    path('members/communications/', include(('members.communications.urls', 'communications'), namespace='communications')),
    path('branches/', include(('branches.urls', 'branches'), namespace='branches')),
    path('schemes/', include(('schemes.urls', 'schemes'), namespace='schemes')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    path('supplements/', include(('supplements.urls', 'supplements'), namespace='supplements')),
    path('sms-templates/', include(('sms_templates.urls', 'sms_templates'), namespace='sms_templates')),
    path('claims/', include(('claims.urls', 'claims'), namespace='claims')),
    path('import_data/', include(('import_data.urls', 'import_data'), namespace='import_data')),
    path('reports/', include(('reports.urls', 'reports'), namespace='reports')),
]

# Serve media in development
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
