from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from decimal import Decimal
from .models import Department
from .serializers import DepartmentSerializer
from users.permissions import IsAdmin, IsManagerOrAdmin


class DepartmentListView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class DepartmentDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def get_object(self, pk):
        try:
            return Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return None

    def get(self, request, pk):
        dept = self.get_object(pk)
        if not dept:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = DepartmentSerializer(dept)
        return Response(serializer.data)

    def patch(self, request, pk):
        dept = self.get_object(pk)
        if not dept:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = DepartmentSerializer(dept,
                                          data=request.data,
                                          partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        dept = self.get_object(pk)
        if not dept:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = DepartmentSerializer(dept,
                                          data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        dept = self.get_object(pk)
        if not dept:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        dept.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BudgetView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request, pk):
        try:
            dept = Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        total_approved = dept.expenses.filter(status='Approved').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        remaining_budget = dept.budget_limit - total_approved
        return Response({
            "budget_limit": dept.budget_limit,
            "total_approved": total_approved,
            "remaining_budget": remaining_budget
        })
