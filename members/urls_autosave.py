from django.urls import path
from .views_diy_autosave import (
    auto_save_application, 
    mark_application_abandoned, 
    mark_application_completed,
    check_application_exists
)
from .views_diy_incomplete import (
    IncompleteApplicationsListView, 
    IncompleteApplicationDetailView,
    ResumeIncompleteApplicationView,
    ResumeApplicationView,
    DeleteIncompleteApplicationView
)
from .views_diy_api_autosave import get_plans, calculate_premium, get_application_stats
from .views_diy_steps import (
    PersonalDetailsView,
    ContactInfoView,
    BeneficiariesView,
    PolicyDetailsView,
    PaymentOptionsView,
    ReviewView,
    ConfirmationView
)

app_name = 'members'

urlpatterns = [
    # Auto-save API endpoints
    path('api/diy/autosave/', auto_save_application, name='diy_autosave'),
    path('api/diy/mark-abandoned/<uuid:token>/', mark_application_abandoned, name='mark_application_abandoned'),
    path('api/diy/mark-completed/<uuid:token>/', mark_application_completed, name='mark_application_completed'),
    path('api/diy/check-application/<uuid:token>/', check_application_exists, name='check_application_exists'),
    
    # DIY application API endpoints
    path('api/diy/plans/', get_plans, name='diy_get_plans'),
    path('api/diy/calculate-premium/', calculate_premium, name='diy_calculate_premium'),
    path('api/diy/application-stats/', get_application_stats, name='diy_application_stats'),
    
    # Incomplete applications management
    path('diy/incomplete-applications/', IncompleteApplicationsListView.as_view(), name='incomplete_applications'),
    path('diy/incomplete-applications/<uuid:token>/', IncompleteApplicationDetailView.as_view(), name='incomplete_application_detail'),
    path('diy/resume-application/<uuid:token>/', ResumeIncompleteApplicationView.as_view(), name='resume_incomplete_application'),
    path('diy/resume/<uuid:token>/', ResumeApplicationView.as_view(), name='diy_resume_application'),
    path('diy/delete-application/<uuid:token>/', DeleteIncompleteApplicationView.as_view(), name='delete_incomplete_application'),
    
    # DIY application steps
    path('diy/application/step/<int:step>/', PersonalDetailsView.as_view(), name='diy_application_step'),
    path('diy/application/step/1/', PersonalDetailsView.as_view(), name='diy_personal_details'),
    path('diy/application/step/2/', ContactInfoView.as_view(), name='diy_contact_information'),
    path('diy/application/step/3/', BeneficiariesView.as_view(), name='diy_beneficiaries'),
    path('diy/application/step/4/', PolicyDetailsView.as_view(), name='diy_policy_details'),
    path('diy/application/step/5/', PaymentOptionsView.as_view(), name='diy_payment_options'),
    path('diy/application/step/6/', ReviewView.as_view(), name='diy_review_submit'),
    path('diy/application/step/7/', ConfirmationView.as_view(), name='diy_success'),
    
    # DIY application download certificate
    path('diy/download-certificate/<uuid:token>/', ConfirmationView.as_view(), name='diy_download_certificate'),
    
    # DIY application start
    path('diy/start/', PersonalDetailsView.as_view(), name='diy_start'),
]
