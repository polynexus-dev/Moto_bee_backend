from django.contrib import admin
from .models import Garage, DaySchedule, ServiceOffer, CuratedService

@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city_from_address', 'is_active']
    def city_from_address(self, obj): return obj.address[:40]

@admin.register(DaySchedule)
class DayScheduleAdmin(admin.ModelAdmin):
    list_display = ['garage', 'date', 'is_open', 'start_hour', 'end_hour']

@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']

@admin.register(CuratedService)
class CuratedServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'vehicle_type', 'order', 'is_active']
