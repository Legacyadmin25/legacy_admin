"""
Public Enrollment URLs
Separate namespace for public self-service enrollment
"""

from django.urls import path
from . import views_public_enrollment
from .views_short_links import enrollment_short_redirect

app_name = 'public_enrollment'

urlpatterns = [
     path('s/<int:link_id>/', enrollment_short_redirect, name='short_link'),

    # Entry point - validated token
    path('<str:token>/', 
         views_public_enrollment.PublicEnrollmentStartView.as_view(), 
         name='start'),
    
    # Step 1: Personal Details
    path('step1/personal/', 
         views_public_enrollment.Step1PersonalDetailsView.as_view(), 
         name='step1_personal'),
    
    # Step 2: Address
    path('step2/address/', 
         views_public_enrollment.Step2AddressView.as_view(), 
         name='step2_address'),
    
    # Step 3: Plan Selection
    path('step3/plan/', 
         views_public_enrollment.Step3PlanSelectionView.as_view(), 
         name='step3_plan'),
    
    # Step 4: Payment Details (conditional)
    path('step4/payment/', 
         views_public_enrollment.Step4PaymentDetailsView.as_view(), 
         name='step4_payment'),
    
    # Step 5: Conditional Questions
    path('step5/questions/', 
         views_public_enrollment.Step5ConditionalQuestionsView.as_view(), 
         name='step5_questions'),
    
    # Step 6: Consent & Terms
    path('step6/consent/', 
         views_public_enrollment.Step6ConsentAndTermsView.as_view(), 
         name='step6_consent'),
    
    # OTP Verification
    path('otp/verify/', 
         views_public_enrollment.OTPVerificationView.as_view(), 
         name='otp_verify'),
    
    path('otp/resend/', 
         views_public_enrollment.OTPResendView.as_view(), 
         name='otp_resend'),
    
    # Success & Confirmation
    path('success/<int:app_id>/', 
         views_public_enrollment.EnrollmentSuccessView.as_view(), 
         name='success'),
]
