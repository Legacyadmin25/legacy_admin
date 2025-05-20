from django.contrib import admin
from .models import Scheme, Plan

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'fsp_number', 'email', 'phone')

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'premium', 'underwriter', 'min_age', 'max_age', 'scheme')
    list_filter = ('scheme', 'underwriter')
    search_fields = ('name', 'description')
