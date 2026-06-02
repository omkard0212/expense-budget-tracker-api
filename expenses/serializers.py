from rest_framework import serializers
from .models import Expense
from users.serializers import UserProfileSerializer
from departments.serializers import DepartmentSerializer
from departments.models import Department


class ExpenseSerializer(serializers.ModelSerializer):
    # Nested read-only representations
    submitted_by = UserProfileSerializer(read_only=True)
    department_detail = DepartmentSerializer(source='department', read_only=True)

    # Writable FK — accepts department ID on create/update
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all()
    )

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'category', 'status',
            'submitted_by', 'department', 'department_detail',
            'description', 'created_at', 'updated_at',
        ]
        read_only_fields = ['status', 'submitted_by', 'created_at', 'updated_at']
