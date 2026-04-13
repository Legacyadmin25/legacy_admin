from django.urls import include, path

urlpatterns = [
    path('scheme-onboarding/', include(('schemes.onboarding.urls', 'scheme_onboarding'), namespace='scheme_onboarding')),
]
