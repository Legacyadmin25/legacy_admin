from django.contrib import admin
from .models import Claim

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'claim_type', 'amount', 'status', 'created_at')
    list_filter = ('status', 'claim_type')
    search_fields = ('member__first_name', 'member__last_name', 'id')
