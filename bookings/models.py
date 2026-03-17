"""
bookings/models.py — Booking model (lives in tenant schema)
"""
import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('accepted',    'Accepted'),
        ('rejected',    'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('cancelled',   'Cancelled'),
    ]
    VEHICLE_CHOICES = [('bike', 'Bike'), ('scooty', 'Scooty')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings'
    )
    # garage FK references the Garage model in the same tenant schema
    garage = models.ForeignKey(
        'garages.Garage', on_delete=models.CASCADE, related_name='bookings'
    )

    date = models.DateField()
    time = models.CharField(max_length=5)           # "10:00"
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)
    bike_details = models.CharField(max_length=300) # "Honda Activa, MH31 AB1234"
    selected_services = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', db_index=True)
    rejection_note = models.TextField(blank=True)

    # Timestamps per status change
    service_started_at = models.DateTimeField(null=True, blank=True)
    estimated_duration_min = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.id} — {self.customer.email} @ {self.garage.name} [{self.status}]"
