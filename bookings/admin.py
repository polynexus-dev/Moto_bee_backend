from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'garage', 'date', 'time', 'status', 'created_at']
    list_filter = ['status', 'vehicle_type', 'date']
    search_fields = ['customer__email', 'garage__name', 'bike_details']
