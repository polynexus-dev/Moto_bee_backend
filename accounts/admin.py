from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'role', 'phone', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('MOTOBEE', {'fields': ('role', 'phone', 'expo_push_token', 'tenant_schema')}),
    )
