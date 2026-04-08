# settings_app/admin.py (Upgraded Version)

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Branch, Agent, Underwriter, PlanMemberTier, UserProfile, UserGroup, PagePermission, SchemeDocument
from schemes.models import Plan

try:
    from import_export import resources, fields
    from import_export.admin import ImportExportModelAdmin
    from import_export.widgets import BooleanWidget
    IMPORT_EXPORT_AVAILABLE = True
except BaseException:
    resources = None
    fields = None
    BooleanWidget = None
    ImportExportModelAdmin = admin.ModelAdmin
    IMPORT_EXPORT_AVAILABLE = False


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

if IMPORT_EXPORT_AVAILABLE:
    class UnderwriterResource(resources.ModelResource):
        name = fields.Field(column_name='name', attribute='name')
        fsp_number = fields.Field(column_name='fsp_number', attribute='fsp_number')
        is_active = fields.Field(column_name='is_active', attribute='is_active', widget=BooleanWidget())
        email = fields.Field(column_name='email', attribute='email')
        contact_number = fields.Field(column_name='contact_number', attribute='contact_number')
        contact_person = fields.Field(column_name='contact_person', attribute='contact_person')

        class Meta:
            model = Underwriter
            import_id_fields = ('name',)
            fields = ('id', 'name', 'fsp_number', 'is_active', 'email', 'contact_number', 'contact_person')
            export_order = fields

@admin.register(Underwriter)
class UnderwriterAdmin(ImportExportModelAdmin):
    list_display = ('name', 'fsp_number', 'contact_person', 'contact_number', 'is_active')
    search_fields = ('name', 'fsp_number', 'contact_person', 'email')
    list_filter = ('is_active',)
    ordering = ('name',)

    if IMPORT_EXPORT_AVAILABLE:
        resource_class = UnderwriterResource


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
