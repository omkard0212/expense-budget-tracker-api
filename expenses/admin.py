from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'amount', 'category', 'status', 'submitted_by', 'department', 'created_at']
    list_filter = ['status', 'category', 'department']
    search_fields = ['title', 'submitted_by__username']
