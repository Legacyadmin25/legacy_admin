from django.contrib import admin

from .models import Payment, PaymentAllocation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ('id', 'member', 'policy', 'amount', 'date', 'payment_method', 'status')
	list_filter = ('status', 'payment_method', 'date')
	search_fields = ('member__first_name', 'member__last_name', 'policy__policy_number', 'reference_number')


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
	list_display = ('id', 'policy', 'coverage_month', 'allocated_amount', 'scheme', 'agent', 'allocation_status')
	list_filter = ('coverage_month', 'allocation_status', 'scheme')
	search_fields = ('policy__policy_number', 'member__first_name', 'member__last_name', 'agent_name', 'agent_code')
