from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q

from audit.models import AuditLog, DataAccess


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_link', 'action', 'object_link', 'ip_address')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('username', 'object_repr', 'ip_address')
    readonly_fields = ('timestamp', 'user', 'username', 'action', 'ip_address', 
                       'user_agent', 'content_type', 'object_id', 'object_repr', 'data_formatted')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs
        return request.user.is_superuser
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.username)
        return obj.username
    user_link.short_description = 'User'
    user_link.admin_order_field = 'username'
    
    def object_link(self, obj):
        if obj.content_type and obj.object_id:
            try:
                url = reverse(
                    f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                    args=[obj.object_id]
                )
                return format_html('<a href="{}">{}</a>', url, obj.object_repr)
            except:
                # The object might not exist anymore or have no admin URL
                return obj.object_repr
        return obj.object_repr
    object_link.short_description = 'Object'
    object_link.admin_order_field = 'object_repr'
    
    def data_formatted(self, obj):
        """Format the JSON data for better display"""
        if not obj.data:
            return '-'
        
        html = ['<table class="table">']
        if isinstance(obj.data, dict):
            for key, value in obj.data.items():
                html.append(f'<tr><th>{key}</th><td>{value}</td></tr>')
        elif isinstance(obj.data, list):
            for item in obj.data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        html.append(f'<tr><th>{key}</th><td>{value}</td></tr>')
                else:
                    html.append(f'<tr><td colspan="2">{item}</td></tr>')
        else:
            html.append(f'<tr><td colspan="2">{obj.data}</td></tr>')
        
        html.append('</table>')
        return format_html(''.join(html))
    data_formatted.short_description = 'Data Changes'


@admin.register(DataAccess)
class DataAccessAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_link', 'content_type', 'fields_list', 'ip_address')
    list_filter = ('timestamp', 'user', 'content_type')
    search_fields = ('username', 'ip_address', 'access_reason')
    readonly_fields = ('timestamp', 'user', 'username', 'ip_address', 
                       'content_type', 'object_id', 'fields_accessed', 'access_reason')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete data access logs
        return request.user.is_superuser
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.username)
        return obj.username
    user_link.short_description = 'User'
    user_link.admin_order_field = 'username'
    
    def fields_list(self, obj):
        """Display a comma-separated list of accessed fields"""
        if not obj.fields_accessed:
            return '-'
        return ', '.join(obj.fields_accessed)
    fields_list.short_description = 'Fields Accessed'
