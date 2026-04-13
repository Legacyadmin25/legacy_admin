from django.urls import path

from . import views

app_name = 'scheme_onboarding'

urlpatterns = [
    path('start/<str:token>/', views.SchemeOnboardingStartView.as_view(), name='start'),
    path('step1/<str:token>/', views.SchemeOnboardingStep1View.as_view(), name='step1'),
    path('step2/<str:token>/', views.SchemeOnboardingStep2View.as_view(), name='step2'),
    path('review/<str:token>/', views.SchemeOnboardingReviewView.as_view(), name='review'),
    path('submit/<str:token>/', views.SchemeOnboardingSubmitView.as_view(), name='submit'),
    path('branch/list/', views.BranchOnboardingReviewListView.as_view(), name='branch_list'),
    path('branch/<int:pk>/', views.BranchOnboardingDetailView.as_view(), name='branch_detail'),
    path('branch/<int:pk>/approve/', views.BranchOnboardingApproveView.as_view(), name='branch_approve'),
    path('branch/<int:pk>/reopen/', views.BranchOnboardingReopenView.as_view(), name='branch_reopen'),
]
