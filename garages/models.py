"""garages/models.py"""
import uuid
from django.db import models
from django.conf import settings

WEEKDAYS = [
    ('Monday',    'Monday'),
    ('Tuesday',   'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday',  'Thursday'),
    ('Friday',    'Friday'),
    ('Saturday',  'Saturday'),
    ('Sunday',    'Sunday'),
]


class Garage(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner     = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='garage',
        limit_choices_to={'role': 'owner'},
    )
    name      = models.CharField(max_length=200, blank=True)
    address   = models.TextField(blank=True)
    phone     = models.CharField(max_length=15, blank=True)
    latitude  = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    # services stored as {"bike": [...], "scooty": [...]}
    services  = models.JSONField(default=dict, blank=True)
    
    service_prices = models.JSONField(default=dict, blank=True)

    photo      = models.ImageField(upload_to='garages/', null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or f"Garage ({self.owner.email})"


class GarageSchedule(models.Model):
    """Weekly recurring schedule — one row per weekday per garage."""
    garage           = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='schedule')
    day              = models.CharField(max_length=10, choices=WEEKDAYS)
    is_open          = models.BooleanField(default=True)
    start_hour       = models.IntegerField(default=9)
    end_hour         = models.IntegerField(default=18)
    interval_minutes = models.IntegerField(default=60)

    class Meta:
        unique_together = ('garage', 'day')
        ordering = ['id']

    def __str__(self):
        return f"{self.garage.name} — {self.day}"


class ServiceOffer(models.Model):
    title      = models.CharField(max_length=200)
    subtitle   = models.CharField(max_length=300, blank=True)
    image_url  = models.URLField(blank=True)
    bg_color   = models.CharField(max_length=7, default='#1A73E8')
    is_active  = models.BooleanField(default=True)
    order      = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class CuratedService(models.Model):
    VEHICLE_CHOICES = [('both', 'Both'), ('bike', 'Bike'), ('scooty', 'Scooty')]

    name         = models.CharField(max_length=100)
    icon         = models.CharField(max_length=50, blank=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default='both')
    is_active    = models.BooleanField(default=True)
    order        = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name