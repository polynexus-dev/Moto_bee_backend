from django.db import models
from django.conf import settings
import uuid

class Vehicle(models.Model):
    
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    VEHICLE_TYPES = [
        ('bike', 'Bike'),
        ('scooty', 'Scooty')
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )

    type = models.CharField(max_length=10, choices=VEHICLE_TYPES)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.CharField(max_length=4, blank=True)
    registration = models.CharField(max_length=20)
    color = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'registration')

    def __str__(self):
        return f"{self.brand} {self.model} — {self.registration}"