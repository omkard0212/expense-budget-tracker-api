from django.urls import path
from .views import (
    DepartmentListView,
    DepartmentDetailView,
    BudgetView,
)

urlpatterns = [
    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/budget/', BudgetView.as_view(), name='department_budget'),
]
