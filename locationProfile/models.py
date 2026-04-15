from django.db import models
from django.conf import settings

class UserLocationProfile(models.Model):
    TYPE_CHOICES = [
        ('home',   'Home'),
        ('office', 'Office'),
        ('other',  'Other'),
    ]

    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='location_profiles',
    )
    type      = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    label     = models.CharField(max_length=100)
    address   = models.TextField()
    latitude  = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} — {self.label} ({self.type})"