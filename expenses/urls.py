from django.urls import path
from .views import (
    ExpenseListView,
    ExpenseDetailView,
    ExpenseApproveView,
    ExpenseRejectView,
)

urlpatterns = [
    path('expenses/', ExpenseListView.as_view(), name='expense_list'),
    path('expenses/<int:pk>/', ExpenseDetailView.as_view(), name='expense_detail'),
    path('expenses/<int:pk>/approve/', ExpenseApproveView.as_view(), name='expense_approve'),
    path('expenses/<int:pk>/reject/', ExpenseRejectView.as_view(), name='expense_reject'),
]
