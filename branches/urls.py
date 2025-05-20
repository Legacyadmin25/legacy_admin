from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    # Branch Setup
    path('setup/', views.branch_setup, name='branch_setup'),  # For creating/editing branches

    # Branch List (Display all branches)
    path('list/', views.branch_list, name='branch_list'),

    # Branch Edit (Edit a branch)
    path('<int:branch_id>/edit/', views.branch_edit, name='branch_edit'),

    # Branch Details (Display specific branch information)
    path('<int:branch_id>/', views.branch_detail, name='branch_detail'),

    # Branch Deletion (Delete a branch after confirmation)
    path('<int:branch_id>/delete/', views.branch_delete, name='branch_delete'),
]
