from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Expense
from .serializers import ExpenseSerializer
from .filters import ExpenseFilter
from users.permissions import IsManagerOrAdmin


def get_expense_queryset(user):
    if user.role == 'Admin':
        return Expense.objects.all()
    elif user.role == 'Manager':
        return Expense.objects.filter(
            Q(submitted_by=user) | Q(department=user.department)
        )
    else:
        return Expense.objects.filter(submitted_by=user)


class ExpenseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = get_expense_queryset(request.user)
        filterset = ExpenseFilter(request.GET, queryset=queryset)
        if filterset.is_valid():
            queryset = filterset.qs
        serializer = ExpenseSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(submitted_by=request.user,
                            status='Pending')
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return None, 'not_found'
        if user.role == 'Admin':
            return expense, 'ok'
        if user.role == 'Manager':
            if (expense.submitted_by == user or
                    expense.department == user.department):
                return expense, 'ok'
            return None, 'forbidden'
        if expense.submitted_by == user:
            return expense, 'ok'
        return None, 'forbidden'

    def get(self, request, pk):
        expense, result = self.get_object(pk, request.user)
        if result == 'not_found':
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if result == 'forbidden':
            return Response({"detail": "You do not have permission."},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)

    def patch(self, request, pk):
        expense, result = self.get_object(pk, request.user)
        if result == 'not_found':
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if result == 'forbidden':
            return Response({"detail": "You do not have permission."},
                            status=status.HTTP_403_FORBIDDEN)
        if expense.submitted_by != request.user:
            return Response({"detail": "You do not have permission."},
                            status=status.HTTP_403_FORBIDDEN)
        if expense.status != 'Pending':
            return Response({"detail": "Cannot edit an expense that has already been reviewed."},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ExpenseSerializer(expense,
                                       data=request.data,
                                       partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        expense, result = self.get_object(pk, request.user)
        if result == 'not_found':
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'Admin':
            expense.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if result == 'forbidden':
            return Response({"detail": "You do not have permission."},
                            status=status.HTTP_403_FORBIDDEN)
        if expense.submitted_by != request.user:
            return Response({"detail": "You do not have permission."},
                            status=status.HTTP_403_FORBIDDEN)
        if expense.status != 'Pending':
            return Response({"detail": "Cannot delete an expense that has already been reviewed."},
                            status=status.HTTP_400_BAD_REQUEST)
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExpenseApproveView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'Manager':
            if expense.department != request.user.department:
                return Response({"detail": "You do not have permission."},
                                status=status.HTTP_403_FORBIDDEN)
        if expense.status != 'Pending':
            return Response({"detail": "Only Pending expenses can be approved or rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        expense.status = 'Approved'
        expense.save()
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)


class ExpenseRejectView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'Manager':
            if expense.department != request.user.department:
                return Response({"detail": "You do not have permission."},
                                status=status.HTTP_403_FORBIDDEN)
        if expense.status != 'Pending':
            return Response({"detail": "Only Pending expenses can be approved or rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        expense.status = 'Rejected'
        expense.save()
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)
