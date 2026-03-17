"""
garages/models.py — Garage, DaySchedule, ServiceOffer, CuratedService
Lives in TENANT schema (per city/zone).
"""
import uuid
from django.db import models
from django.conf import settings


class Garage(models.Model):
    """A garage/workshop registered on MOTOBEE."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='garage',
        limit_choices_to={'role': 'owner'},
    )
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Services stored as JSON lists: ["Oil Change", "Chain Service", ...]
    bike_services = models.JSONField(default=list, blank=True)
    scooty_services = models.JSONField(default=list, blank=True)

    # Garage profile photo
    photo = models.ImageField(upload_to='garages/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DaySchedule(models.Model):
    """Working schedule for a specific date in a garage."""
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField(db_index=True)
    is_open = models.BooleanField(default=True)
    start_hour = models.IntegerField(default=9)   # 9 = 9:00 AM
    end_hour = models.IntegerField(default=18)    # 18 = 6:00 PM
    interval_minutes = models.IntegerField(default=60)

    # Computed slots stored as JSON for fast reads:
    # [{"id": "0900", "time": "09:00", "is_booked": false, "booked_by": null}]
    slots = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('garage', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.garage.name} — {self.date}"

    def generate_slots(self):
        """Regenerate slot list from start_hour, end_hour, interval_minutes."""
        from datetime import time
        slots = []
        current = self.start_hour * 60  # minutes from midnight
        end = self.end_hour * 60
        while current < end:
            h, m = divmod(current, 60)
            slot_id = f"{h:02d}{m:02d}"
            slots.append({
                'id': slot_id,
                'time': f"{h:02d}:{m:02d}",
                'is_booked': False,
                'booked_by': None,
            })
            current += self.interval_minutes
        self.slots = slots
        return slots

    def mark_slot_booked(self, slot_id: str, booked_by: str):
        for slot in self.slots:
            if slot['id'] == slot_id:
                slot['is_booked'] = True
                slot['booked_by'] = booked_by
                break
        self.save()

    def unmark_slot(self, slot_id: str):
        for slot in self.slots:
            if slot['id'] == slot_id:
                slot['is_booked'] = False
                slot['booked_by'] = None
                break
        self.save()


class ServiceOffer(models.Model):
    """Promotional banner/offer shown on the customer home screen."""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    image_url = models.URLField(blank=True)
    bg_color = models.CharField(max_length=7, default='#1A73E8')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class CuratedService(models.Model):
    """Quick-access service tiles on home screen (Oil Change, Tyre Repair, etc.)."""
    VEHICLE_CHOICES = [('both', 'Both'), ('bike', 'Bike'), ('scooty', 'Scooty')]

    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name for React Native")
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default='both')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name
