from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from departments.models import Department
from expenses.models import Expense
from users.models import CustomUser


def make_dept(name='Engineering', budget=50000):
    return Department.objects.create(name=name, budget_limit=budget)


def make_user(username, role='Employee', department=None, password='testpass123'):
    return CustomUser.objects.create_user(
        username=username, password=password,
        email=f'{username}@test.com', role=role, department=department,
    )


def make_expense(user, dept, title='Test Expense', amount='100.00',
                 category='Travel', exp_status='Pending'):
    return Expense.objects.create(
        title=title, amount=amount, category=category,
        status=exp_status, submitted_by=user, department=dept,
    )


def get_access(client, username, password='testpass123'):
    resp = client.post(reverse('login'), {'username': username, 'password': password}, format='json')
    return resp.data['access']


class ExpenseListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept1 = make_dept('Dept1')
        self.dept2 = make_dept('Dept2')
        self.admin = make_user('admin1', role='Admin', department=self.dept1)
        self.manager = make_user('mgr1', role='Manager', department=self.dept1)
        self.emp1 = make_user('emp1', role='Employee', department=self.dept1)
        self.emp2 = make_user('emp2', role='Employee', department=self.dept2)
        self.exp1 = make_expense(self.emp1, self.dept1, 'Emp1 Travel')
        self.exp2 = make_expense(self.emp2, self.dept2, 'Emp2 Food', category='Food')

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_employee_sees_only_own_expenses(self):
        self._auth('emp1')
        resp = self.client.get(reverse('expense_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [e['title'] for e in resp.data]
        self.assertIn('Emp1 Travel', titles)
        self.assertNotIn('Emp2 Food', titles)

    def test_manager_sees_dept_expenses(self):
        self._auth('mgr1')
        resp = self.client.get(reverse('expense_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [e['title'] for e in resp.data]
        self.assertIn('Emp1 Travel', titles)
        self.assertNotIn('Emp2 Food', titles)

    def test_admin_sees_all_expenses(self):
        self._auth('admin1')
        resp = self.client.get(reverse('expense_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_unauthenticated_denied(self):
        resp = self.client.get(reverse('expense_list'))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_expense_success(self):
        self._auth('emp1')
        data = {
            'title': 'New Expense',
            'amount': '200.00',
            'category': 'Food',
            'department': self.dept1.pk,
            'description': 'lunch',
        }
        resp = self.client.post(reverse('expense_list'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'Pending')
        self.assertEqual(resp.data['submitted_by']['username'], 'emp1')

    def test_create_expense_missing_required_field(self):
        self._auth('emp1')
        data = {'amount': '100.00', 'category': 'Travel'}  # missing title and department
        resp = self.client.post(reverse('expense_list'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_status(self):
        self._auth('admin1')
        make_expense(self.emp1, self.dept1, 'Approved One', exp_status='Approved')
        resp = self.client.get(reverse('expense_list') + '?status=Approved')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for e in resp.data:
            self.assertEqual(e['status'], 'Approved')

    def test_filter_by_category(self):
        self._auth('admin1')
        resp = self.client.get(reverse('expense_list') + '?category=Food')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for e in resp.data:
            self.assertEqual(e['category'], 'Food')


class ExpenseDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = make_dept()
        self.other_dept = make_dept('OtherDept')
        self.admin = make_user('admin1', role='Admin', department=self.dept)
        self.manager = make_user('mgr1', role='Manager', department=self.dept)
        self.emp1 = make_user('emp1', role='Employee', department=self.dept)
        self.emp2 = make_user('emp2', role='Employee', department=self.other_dept)
        self.expense = make_expense(self.emp1, self.dept, 'My Expense')

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_owner_can_get(self):
        self._auth('emp1')
        resp = self.client.get(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_other_employee_cannot_get(self):
        self._auth('emp2')
        resp = self.client.get(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_same_dept_can_get(self):
        self._auth('mgr1')
        resp = self.client.get(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_get(self):
        self._auth('admin1')
        resp = self.client.get(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_not_found(self):
        self._auth('admin1')
        resp = self.client.get(reverse('expense_detail', args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_patch_pending(self):
        self._auth('emp1')
        resp = self.client.patch(
            reverse('expense_detail', args=[self.expense.pk]),
            {'title': 'Updated Title'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'Updated Title')

    def test_owner_cannot_patch_approved(self):
        self.expense.status = 'Approved'
        self.expense.save()
        self._auth('emp1')
        resp = self.client.patch(
            reverse('expense_detail', args=[self.expense.pk]),
            {'title': 'Try Update'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_employee_cannot_patch(self):
        self._auth('emp2')
        resp = self.client.patch(
            reverse('expense_detail', args=[self.expense.pk]),
            {'title': 'Hack'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_pending(self):
        self._auth('emp1')
        resp = self.client.delete(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_owner_cannot_delete_approved(self):
        self.expense.status = 'Approved'
        self.expense.save()
        self._auth('emp1')
        resp = self.client.delete(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_delete_any(self):
        self.expense.status = 'Approved'
        self.expense.save()
        self._auth('admin1')
        resp = self.client.delete(reverse('expense_detail', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class ExpenseApproveRejectTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = make_dept()
        self.other_dept = make_dept('OtherDept')
        self.admin = make_user('admin1', role='Admin', department=self.dept)
        self.manager = make_user('mgr1', role='Manager', department=self.dept)
        self.other_manager = make_user('mgr2', role='Manager', department=self.other_dept)
        self.emp = make_user('emp1', role='Employee', department=self.dept)
        self.expense = make_expense(self.emp, self.dept)

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_manager_can_approve_own_dept(self):
        self._auth('mgr1')
        resp = self.client.post(reverse('expense_approve', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'Approved')

    def test_manager_cannot_approve_other_dept(self):
        self._auth('mgr2')
        resp = self.client.post(reverse('expense_approve', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve(self):
        self._auth('admin1')
        resp = self.client.post(reverse('expense_approve', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'Approved')

    def test_employee_cannot_approve(self):
        self._auth('emp1')
        resp = self.client.post(reverse('expense_approve', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_approve_already_approved(self):
        self.expense.status = 'Approved'
        self.expense.save()
        self._auth('admin1')
        resp = self.client.post(reverse('expense_approve', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_reject_own_dept(self):
        self._auth('mgr1')
        resp = self.client.post(reverse('expense_reject', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'Rejected')

    def test_manager_cannot_reject_other_dept(self):
        self._auth('mgr2')
        resp = self.client.post(reverse('expense_reject', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_reject_already_rejected(self):
        self.expense.status = 'Rejected'
        self.expense.save()
        self._auth('admin1')
        resp = self.client.post(reverse('expense_reject', args=[self.expense.pk]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_not_found(self):
        self._auth('admin1')
        resp = self.client.post(reverse('expense_approve', args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
