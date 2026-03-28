"""notifications/models.py"""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_booking',  'New Booking'),
        ('accepted',     'Booking Accepted'),
        ('rejected',     'Booking Rejected'),
        ('in_progress',  'Service Started'),
        ('completed',    'Service Completed'),
        ('cancelled',    'Booking Cancelled'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    booking          = models.ForeignKey(
        'bookings.Booking', on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title            = models.CharField(max_length=200)
    body             = models.TextField()
    is_read          = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] → {self.recipient.email}"


class FCMToken(models.Model):
    """Stores Firebase Cloud Messaging device tokens per user."""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fcm_tokens'
    )
    token      = models.CharField(max_length=512, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} — {self.token[:30]}…"
