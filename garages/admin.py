from django.contrib import admin
from .models import Garage, GarageSchedule, ServiceOffer, CuratedService

@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'phone', 'is_active']

@admin.register(GarageSchedule)
class GarageScheduleAdmin(admin.ModelAdmin):
    list_display = ['garage', 'day', 'is_open', 'start_hour', 'end_hour']

@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']

@admin.register(CuratedService)
class CuratedServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'vehicle_type', 'order', 'is_active']