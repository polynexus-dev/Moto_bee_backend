"""
accounts/tests.py — Auth endpoint tests
Run: python manage.py test accounts
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.me_url = '/api/v1/auth/me/'

    def test_register_customer(self):
        res = self.client.post(self.register_url, {
            'name': 'Rahul Sharma',
            'email': 'rahul@test.com',
            'phone': '9876543210',
            'password': 'testpass123',
            'role': 'customer',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', res.data)
        self.assertEqual(res.data['user']['role'], 'customer')

    def test_register_owner(self):
        res = self.client.post(self.register_url, {
            'name': 'Amit Garage',
            'email': 'amit@test.com',
            'phone': '9876543211',
            'password': 'testpass123',
            'role': 'owner',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user']['role'], 'owner')

    def test_register_duplicate_email(self):
        payload = {'name': 'A', 'email': 'dup@test.com',
                   'phone': '9000000000', 'password': 'pass12345', 'role': 'customer'}
        self.client.post(self.register_url, payload)
        res = self.client.post(self.register_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        User.objects.create_user(username='test@test.com', email='test@test.com',
                                  password='pass12345', role='customer')
        res = self.client.post(self.login_url, {'email': 'test@test.com', 'password': 'pass12345'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)

    def test_login_wrong_password(self):
        User.objects.create_user(username='test2@test.com', email='test2@test.com',
                                  password='pass12345', role='customer')
        res = self.client.post(self.login_url, {'email': 'test2@test.com', 'password': 'wrong'})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user(self):
        user = User.objects.create_user(username='me@test.com', email='me@test.com',
                                         password='pass12345', role='customer')
        self.client.force_authenticate(user=user)
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['role'], 'customer')
