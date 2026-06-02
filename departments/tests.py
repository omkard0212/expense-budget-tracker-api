from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from departments.models import Department
from users.models import CustomUser


def make_user(username, role='Employee', department=None, password='testpass123'):
    return CustomUser.objects.create_user(
        username=username, password=password,
        email=f'{username}@test.com', role=role, department=department,
    )


def make_dept(name='Engineering', budget=10000):
    return Department.objects.create(name=name, budget_limit=budget)


def get_access(client, username, password='testpass123'):
    resp = client.post(reverse('login'), {'username': username, 'password': password}, format='json')
    return resp.data['access']


class DepartmentListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin1', role='Admin')
        self.employee = make_user('emp1', role='Employee')
        self.dept = make_dept()

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_departments_authenticated(self):
        self._auth('emp1')
        resp = self.client.get(reverse('department_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_unauthenticated(self):
        resp = self.client.get(reverse('department_list'))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_department_as_admin(self):
        self._auth('admin1')
        data = {'name': 'Marketing', 'budget_limit': '5000.00', 'description': ''}
        resp = self.client.post(reverse('department_list'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['name'], 'Marketing')

    def test_create_department_as_employee_forbidden(self):
        self._auth('emp1')
        data = {'name': 'HR', 'budget_limit': '3000.00'}
        resp = self.client.post(reverse('department_list'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_department_unauthenticated(self):
        data = {'name': 'HR', 'budget_limit': '3000.00'}
        resp = self.client.post(reverse('department_list'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class DepartmentDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin1', role='Admin')
        self.employee = make_user('emp1', role='Employee')
        self.dept = make_dept('Finance', 20000)

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_get_detail_authenticated(self):
        self._auth('emp1')
        resp = self.client.get(reverse('department_detail', args=[self.dept.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'Finance')

    def test_get_detail_not_found(self):
        self._auth('emp1')
        resp = self.client.get(reverse('department_detail', args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_as_admin(self):
        self._auth('admin1')
        resp = self.client.patch(
            reverse('department_detail', args=[self.dept.pk]),
            {'budget_limit': '25000.00'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(str(resp.data['budget_limit']), '25000.00')

    def test_patch_as_employee_forbidden(self):
        self._auth('emp1')
        resp = self.client.patch(
            reverse('department_detail', args=[self.dept.pk]),
            {'budget_limit': '1.00'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_as_admin(self):
        self._auth('admin1')
        resp = self.client.delete(reverse('department_detail', args=[self.dept.pk]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Department.objects.filter(pk=self.dept.pk).exists())

    def test_delete_as_employee_forbidden(self):
        self._auth('emp1')
        resp = self.client.delete(reverse('department_detail', args=[self.dept.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class BudgetViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = make_dept('Ops', 10000)
        self.manager = make_user('mgr1', role='Manager', department=self.dept)
        self.employee = make_user('emp1', role='Employee', department=self.dept)

    def _auth(self, username):
        token = get_access(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_budget_as_manager(self):
        self._auth('mgr1')
        resp = self.client.get(reverse('department_budget', args=[self.dept.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('budget_limit', resp.data)
        self.assertIn('remaining_budget', resp.data)
        self.assertIn('total_approved', resp.data)

    def test_budget_as_employee_forbidden(self):
        self._auth('emp1')
        resp = self.client.get(reverse('department_budget', args=[self.dept.pk]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_budget_not_found(self):
        self._auth('mgr1')
        resp = self.client.get(reverse('department_budget', args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
