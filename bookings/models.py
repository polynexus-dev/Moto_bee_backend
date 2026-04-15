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
    
    # ── Per-item ──────────────────────────────────────────────────────────
    # estimated_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── Order-level billing ───────────────────────────────────────────────
    manifest_id       = models.CharField(max_length=50, blank=True, default='')
    services_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promo_code        = models.CharField(max_length=30, blank=True, default='')
    gst               = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cess              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status    = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
        default='pending'
    )
    payment_method    = models.CharField(max_length=30, blank=True, default='cash')
    
    # ✅ Delivery location fields
    delivery_address   = models.TextField(blank=True, null=True)
    delivery_latitude  = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.id} — {self.customer.email} @ {self.garage.name} [{self.status}]"
