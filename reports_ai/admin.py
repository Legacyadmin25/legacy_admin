from django.contrib import admin
from .models import ReportQuery, ReportExecutionLog, SavedReport


class ReportExecutionLogInline(admin.TabularInline):
    model = ReportExecutionLog
    extra = 0
    readonly_fields = ('status', 'executed_at', 'execution_time', 'record_count', 'error_message')
    can_delete = False
    show_change_link = True


@admin.register(ReportQuery)
class ReportQueryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'report_type', 'created_at', 'is_favorite')
    list_filter = ('report_type', 'is_favorite', 'created_at')
    search_fields = ('original_query', 'user__email')
    readonly_fields = ('created_at',)
    inlines = [ReportExecutionLogInline]
    date_hierarchy = 'created_at'
    list_select_related = ('user',)


@admin.register(ReportExecutionLog)
class ReportExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_query', 'status', 'executed_at', 'execution_time', 'record_count')
    list_filter = ('status', 'executed_at')
    search_fields = ('report_query__original_query', 'report_query__user__email')
    readonly_fields = ('executed_at', 'execution_time', 'record_count', 'error_message')
    date_hierarchy = 'executed_at'
    list_select_related = ('report_query', 'report_query__user')


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at', 'last_accessed')
    search_fields = ('name', 'user__email', 'report_query__original_query')
    list_filter = ('created_at', 'last_accessed')
    readonly_fields = ('created_at', 'last_accessed')
    date_hierarchy = 'created_at'
    list_select_related = ('user', 'report_query')
