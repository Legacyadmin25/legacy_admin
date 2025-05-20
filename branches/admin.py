from django.contrib import admin
from .models import Branch
from schemes.models import Scheme

class SchemeInline(admin.TabularInline):
    model = Scheme
    extra = 1

class BranchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'phone', 'cell', 'town', 'province', 'region',
        'postal_code', 'modified_user', 'modified_date'
    ]
    inlines = [SchemeInline]

# Register models
admin.site.register(Branch, BranchAdmin)
