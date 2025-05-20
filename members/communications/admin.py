from django.contrib import admin
from members.communications.models import SMSLog

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'status', 'sent_at')
    search_fields = ('phone_number', 'message')
    list_filter = ('status',)
