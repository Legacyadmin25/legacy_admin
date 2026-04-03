from django.urls import path
from . import views_diy_v2 as views
from . import views_diy_api
from .views_diy_resume import DIYResumeApplicationView, DIYSaveForLaterView
from .views_diy_premium import CalculatePremiumView
from .views_diy_status import CheckApplicationStatusView
from .views_diy_documents import UploadDocumentView, DeleteDocumentView
from .views_diy_pdf import GeneratePDFView
from .views_diy_certificate import DownloadCertificateView, VerifyCertificateView
from .views_diy_chat import DIYChatView

app_name = 'members'

urlpatterns = [
    # Main application flow
    path('diy/start/', views.DIYStartView.as_view(), name='diy_start'),
    path('diy/start/<str:agent_code>/', views.DIYStartView.as_view(), name='diy_start_with_agent'),
    path('diy/application/start/<uuid:agent_token>/', views.DIYStartView.as_view(), name='diy_application_start'),
    
    # 9-Step Application Flow
    path('diy/step1/personal-details/', views.DIYPersonalDetailsView.as_view(), name='diy_personal_details'),
    path('diy/step2/policy-selection/', views.DIYPolicySelectionView.as_view(), name='diy_policy_selection'),
    path('diy/step3/spouse-information/', views.DIYSpouseInformationView.as_view(), name='diy_spouse_information'),
    path('diy/step4/dependents/', views.DIYDependentsView.as_view(), name='diy_dependents'),
    path('diy/step5/beneficiaries/', views.DIYBeneficiariesView.as_view(), name='diy_beneficiaries'),
    path('diy/step6/payment-options/', views.DIYPaymentOptionsView.as_view(), name='diy_payment_options'),
    path('diy/step7/otp-verification/', views.DIYOTPVerificationView.as_view(), name='diy_otp_verification'),
    path('diy/step8/review/', views.DIYReviewView.as_view(), name='diy_review'),
    path('diy/step9/confirmation/<uuid:application_id>/', views.DIYConfirmationView.as_view(), name='diy_confirmation'),
    
    # Resume Application
    path('diy/resume/<str:token>/', DIYResumeApplicationView.as_view(), name='diy_resume'),
    path('diy/save-for-later/', DIYSaveForLaterView.as_view(), name='diy_save_for_later'),
    
    # API endpoints
    path('api/diy/calculate-premium/', CalculatePremiumView.as_view(), name='diy_calculate_premium'),
    path('api/diy/check-status/', CheckApplicationStatusView.as_view(), name='diy_check_status'),
    
    # New API endpoints using function-based views
    path('api/diy/process-id-document/', views_diy_api.process_id_document, name='diy_process_id_document'),
    path('api/diy/validate-id/', views_diy_api.validate_id_number, name='diy_validate_id'),
    path('api/diy/generate-otp/', views_diy_api.generate_otp, name='diy_generate_otp'),
    path('api/diy/verify-otp/', views_diy_api.verify_otp, name='diy_verify_otp'),
    path('api/diy/ask-ai-about-plan/', views_diy_api.ask_ai_about_plan, name='diy_ask_ai_about_plan'),
    
    # Document management
    path('api/diy/upload-document/', UploadDocumentView.as_view(), name='diy_upload_document'),
    path('api/diy/delete-document/', DeleteDocumentView.as_view(), name='diy_delete_document'),
    
    # PDF generation
    path('api/diy/generate-pdf/', GeneratePDFView.as_view(), name='diy_generate_pdf'),
    path('diy/download-certificate/<uuid:application_id>/', DownloadCertificateView.as_view(), name='diy_download_certificate'),
    path('diy/verify-certificate/<uuid:application_id>/', VerifyCertificateView.as_view(), name='diy_verify_certificate'),
    
    # AI Chat
    path('diy/chat/<uuid:application_id>/', DIYChatView.as_view(), name='diy_chat'),
]
