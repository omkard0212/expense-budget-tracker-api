import django_filters
from .models import Expense


class ExpenseFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = Expense
        fields = ['status', 'category', 'department', 'start_date', 'end_date']
