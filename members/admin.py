from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display  = ('first_name', 'last_name', 'id_number', 'phone_number')
    search_fields = ('first_name', 'last_name', 'id_number', 'phone_number')
