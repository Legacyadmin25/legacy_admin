# settings_app/admin.py (Upgraded Version)

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Branch, Agent, Underwriter, PlanMemberTier, UserProfile, UserGroup, PagePermission, SchemeDocument
from schemes.models import Plan


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'town', 'province', 'phone')
    search_fields = ('name', 'code', 'town', 'province')
    list_filter = ('province', 'region')
    ordering = ('name',)

# settings_app/admin.py

from django.contrib import admin
from .models import Agent

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'surname',
        'scheme',
        'contact_number',
        'email',
        'diy_token',
        'diy_token_created',
        'notes',  # exposed in list view (optional)
    )
    list_filter = ('scheme',)
    ordering = ('surname',)
    readonly_fields = ('diy_token', 'diy_token_created')
    
    # Define the fields and their order in the change form
    fields = (
        'full_name',
        'surname',
        'scheme',
        'contact_number',
        'email',
        'id_number',
        'passport_number',
        'commission_percentage',
        'commission_rand_value',
        'address1',
        'address2',
        'address3',
        'code',
        'notes',            # editable internal notes
        'diy_token',
        'diy_token_created',
    )
    
    # (Optional) enable search by name or email
    search_fields = ('full_name', 'surname', 'email')



@admin.register(Underwriter)
class UnderwriterAdmin(admin.ModelAdmin):
    list_display = ('name', 'fsp_number', 'contact_person', 'contact_number')
    search_fields = ('name', 'fsp_number', 'contact_person')
    ordering = ('name',)


@admin.register(PlanMemberTier)
class PlanMemberTierAdmin(admin.ModelAdmin):
    list_display = ('plan', 'user_type', 'age_from', 'age_to', 'cover', 'premium')
    search_fields = ('plan__name', 'user_type')
    ordering = ('plan', 'user_type')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch', 'is_admin')
    search_fields = ('user__username', 'branch__name')
    list_filter = ('branch', 'is_admin')
    ordering = ('user',)

@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

# settings_app/admin.py
from django.contrib import admin
from .models import PagePermission

@admin.register(PagePermission)
class PagePermissionAdmin(admin.ModelAdmin):
    list_display = ('group', 'page_name', 'has_rights', 'is_read', 'is_write', 'is_update', 'is_payment_reversal',)
    search_fields = ('group__name', 'page_name')
    list_filter = ('group',)
    ordering = ('group', 'page_name')


@admin.register(SchemeDocument)
class SchemeDocumentAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'name', 'created_at')
    search_fields = ('scheme__name', 'name')
    ordering = ('scheme', 'created_at')
