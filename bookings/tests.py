"""
bookings/tests.py — Booking lifecycle tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from garages.models import Garage, DaySchedule

User = get_user_model()


class BookingLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='c@test.com', email='c@test.com',
            password='pass', role='customer')
        self.owner = User.objects.create_user(
            username='o@test.com', email='o@test.com',
            password='pass', role='owner')
        self.garage = Garage.objects.create(
            owner=self.owner, name='Test Garage',
            address='Test Address', phone='9000000000',
            latitude=21.14, longitude=79.08,
            bike_services=['Oil Change'],
        )
        # Create an open schedule
        schedule = DaySchedule(garage=self.garage, date='2026-06-01', is_open=True,
                               start_hour=9, end_hour=11, interval_minutes=60)
        schedule.generate_slots()
        schedule.save()

    def _book(self):
        self.client.force_authenticate(user=self.customer)
        return self.client.post('/api/v1/bookings/', {
            'garage': str(self.garage.id),
            'date': '2026-06-01',
            'time': '09:00',
            'vehicle_type': 'bike',
            'bike_details': 'Honda CB, MH31 XY1234',
        })

    def test_create_booking(self):
        res = self._book()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'pending')

    def test_double_booking_blocked(self):
        self._book()
        res = self._book()  # same slot
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_accept(self):
        booking_id = self._book().data['id']
        self.client.force_authenticate(user=self.owner)
        res = self.client.patch(f'/api/v1/bookings/{booking_id}/accept/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'accepted')

    def test_full_lifecycle(self):
        booking_id = self._book().data['id']
        self.client.force_authenticate(user=self.owner)
        self.client.patch(f'/api/v1/bookings/{booking_id}/accept/')
        self.client.patch(f'/api/v1/bookings/{booking_id}/start/')
        res = self.client.patch(f'/api/v1/bookings/{booking_id}/complete/')
        self.assertEqual(res.data['status'], 'completed')

    def test_customer_cancel(self):
        booking_id = self._book().data['id']
        res = self.client.patch(f'/api/v1/bookings/{booking_id}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'cancelled')
