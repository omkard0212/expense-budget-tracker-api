from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from departments.models import Department
from users.models import CustomUser


def make_user(username, role='Employee', department=None, password='testpass123'):
    user = CustomUser.objects.create_user(
        username=username,
        password=password,
        email=f'{username}@test.com',
        role=role,
        department=department,
    )
    return user


def get_tokens(client, username, password='testpass123'):
    resp = client.post(reverse('login'), {'username': username, 'password': password}, format='json')
    return resp.data.get('access'), resp.data.get('refresh')


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'strongpass1',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'Employee',
        }
        resp = self.client.post(reverse('register'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['username'], 'newuser')
        self.assertNotIn('password', resp.data)

    def test_register_missing_password(self):
        data = {'username': 'nopass', 'email': 'nopass@test.com'}
        resp = self.client.post(reverse('register'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        data = {'username': 'shortpw', 'password': '123', 'email': 'x@x.com'}
        resp = self.client.post(reverse('register'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        make_user('dupuser')
        data = {'username': 'dupuser', 'password': 'testpass123', 'email': 'dup@x.com'}
        resp = self.client.post(reverse('register'), data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('loginuser')

    def test_login_success(self):
        resp = self.client.post(reverse('login'), {'username': 'loginuser', 'password': 'testpass123'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_wrong_password(self):
        resp = self.client.post(reverse('login'), {'username': 'loginuser', 'password': 'wrong'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        access, refresh = get_tokens(self.client, 'loginuser')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = self.client.post(reverse('logout'), {'refresh': refresh}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_unauthenticated(self):
        resp = self.client.post(reverse('logout'), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserMeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('meuser')
        access, _ = get_tokens(self.client, 'meuser')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_get_me(self):
        resp = self.client.get(reverse('user_me'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'meuser')

    def test_patch_me(self):
        resp = self.client.patch(reverse('user_me'), {'first_name': 'Updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['first_name'], 'Updated')

    def test_patch_me_cannot_change_role(self):
        resp = self.client.patch(reverse('user_me'), {'role': 'Admin'}, format='json')
        # role field is not in UserUpdateSerializer, so it should be ignored
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'Employee')

    def test_me_unauthenticated(self):
        self.client.credentials()
        resp = self.client.get(reverse('user_me'))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserListDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin1', role='Admin')
        self.employee = make_user('emp1', role='Employee')

    def _auth(self, username):
        access, _ = get_tokens(self.client, username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_list_users_as_admin(self):
        self._auth('admin1')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_users_as_employee_forbidden(self):
        self._auth('emp1')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_detail_as_admin(self):
        self._auth('admin1')
        resp = self.client.get(reverse('user_detail', args=[self.employee.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'emp1')

    def test_get_user_detail_not_found(self):
        self._auth('admin1')
        resp = self.client.get(reverse('user_detail', args=[9999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_user_soft_deletes(self):
        self._auth('admin1')
        resp = self.client.delete(reverse('user_detail', args=[self.employee.pk]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

    def test_patch_user_as_employee_forbidden(self):
        self._auth('emp1')
        resp = self.client.patch(reverse('user_detail', args=[self.admin.pk]), {'first_name': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
