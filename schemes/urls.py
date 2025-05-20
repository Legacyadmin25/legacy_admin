from django.urls import path
from schemes.views import (
    SchemeListView, SchemeCreateView,
    SchemeUpdateView, SchemeDeleteView
)

app_name = 'schemes'

urlpatterns = [
    path('', SchemeListView.as_view(), name='scheme_list'),
    path('add/', SchemeCreateView.as_view(), name='scheme_create'),
    path('edit/<int:pk>/', SchemeUpdateView.as_view(), name='scheme_edit'),
    path('delete/<int:pk>/', SchemeDeleteView.as_view(), name='scheme_delete'),
]
