from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'department', 'is_active', 'is_staff']
    list_filter = ['role', 'department', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'department', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'department', 'phone')}),
    )
