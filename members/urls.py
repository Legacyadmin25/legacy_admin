from django.urls import path, include
from . import views
from .views_find_policy import find_policy
from .views_policy_detail import (
    policy_detail, add_dependent, add_beneficiary, 
    delete_dependent, delete_beneficiary
)
from .views_diy import diy_signup_start  # Legacy DIY view
from .views_multi_step import (
    step1_personal, step2_policy_details, step3_spouse_info,
    step4_children_info, step5_beneficiaries, step6_payment_options,
    step7_otp_verification, step8_policy_summary, step9_policy_confirmation,
    IncompleteApplicationsList,
)
from .api_views import search_suggestions
from .export_views import export_search_results
from .views_ai_search import ai_search_assistant
from .views_ai_summary import generate_policy_summary
from .views_ai import get_payment_ai_summary

# Import the new DIY URLs
from . import urls_diy

# Import TemplateView for simple template rendering
from django.views.generic import TemplateView

app_name = 'members'

urlpatterns = [
    # Policy creation steps (steps 1 to 9) - New multi-step flow
    path('policy/create/step1/',                                 step1_personal,                  name='step1_personal'),
    path('policy/create/step2/<int:pk>/',                       step2_policy_details,            name='step2_policy_details'),
    path('policy/create/step3/<int:pk>/spouse/',                step3_spouse_info,               name='step3_spouse_info'),
    path('policy/create/step4/<int:pk>/children/',              step4_children_info,             name='step4_children_info'),
    path('policy/create/step5/<int:pk>/beneficiaries/',         step5_beneficiaries,             name='step5_beneficiaries'),
    path('policy/create/step6/<int:pk>/payment/',               step6_payment_options,           name='step6_payment_options'),
    path('policy/create/step7/<int:pk>/otp-verification/',      step7_otp_verification,          name='step7_otp_verification'),
    path('policy/create/step8/<int:pk>/summary/',               step8_policy_summary,            name='step8_policy_summary'),
    path('policy/create/step9/<int:pk>/confirmation/',          step9_policy_confirmation,       name='step9_policy_confirmation'),
    
    # Incomplete applications
    path('applications/incomplete/',                            IncompleteApplicationsList.as_view(), name='incomplete_applications'),

    # Find policy functionality
    path('find/',                                               find_policy,               name='find_policy'),

    # Policy detail page and actions
    path('detail/<int:policy_id>/',                             policy_detail,             name='policy_detail'),
    path('detail/<int:policy_id>/add-dependent/',                add_dependent,             name='add_dependent'),
    path('detail/<int:policy_id>/add-beneficiary/',              add_beneficiary,           name='add_beneficiary'),
    path('detail/<int:policy_id>/delete-dependent/<int:dep_id>/',    delete_dependent,    name='delete_dependent'),
    path('detail/<int:policy_id>/delete-beneficiary/<int:ben_id>/', delete_beneficiary,  name='delete_beneficiary'),
    
    # AI Payment Summary
    path('detail/<int:policy_id>/payment-ai-summary/', get_payment_ai_summary, name='get_payment_ai_summary'),

    # AJAX actions for OTP and certificate resend
    path('ajax/resend-otp/<int:policy_id>/',                    views.resend_otp,                name='ajax_resend_otp'),
    path('ajax/resend-certificate/<int:policy_id>/',            views.resend_certificate_email,  name='ajax_resend_certificate'),
    
    # API endpoints for search functionality
    path('api/search-suggestions/',                             search_suggestions,              name='search_suggestions'),
    path('api/ai-search-assistant/',                            ai_search_assistant,             name='ai_search_assistant'),
    path('api/policy/<int:policy_id>/ai-summary/',              generate_policy_summary,         name='generate_policy_summary'),
    path('export-search-results/',                              export_search_results,           name='export_search_results'),
    path('policy/create/step7/<int:pk>/resend-otp/',            views.resend_otp,                name='resend_otp'),
    
    # Policy document download
    path('policy/<int:pk>/document/',                          views.download_policy_document,   name='download_policy_document'),

    # Member list and general signup pages
    path('',                                                    find_policy,               name='member_list'),

    # Legacy DIY signup process (deprecated, will be removed in future)
    path('signup/<str:token>/',                                 diy_signup_start,                name='diy_signup_start'),
    path('diy/<str:token>/welcome/',                            diy_signup_start,                name='diy_welcome'),
    
    # New DIY Application Flow
    path('diy-new/', include(urls_diy)),

    # Add the new URL for downloading the policy certificate
    path('policy/<int:policy_id>/download/certificate/',         views.download_policy_certificate, name='download_policy_certificate'),
    
    # ID validation test page
    path('id-test/', TemplateView.as_view(template_name='members/id_test.html'), name='id_test'),
]
