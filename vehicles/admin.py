from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "owner",
        "type",
        "brand",
        "model",
        "registration",
        "color",
        "created_at",
    )

    list_filter = (
        "type",
        "brand",
        "created_at",
    )

    search_fields = (
        "registration",
        "brand",
        "model",
        "owner__email",
        "owner__username",
    )

    readonly_fields = ("created_at",)

    ordering = ("-created_at",)