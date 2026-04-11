# ""bookings/serializers.py"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    garage_name   = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_name', 'garage', 'garage_name',
            'date', 'time', 'vehicle_type', 'bike_details', 'selected_services',
            'status', 'rejection_note',
            'service_started_at', 'estimated_duration_min', 'completed_at',
            'created_at', 'updated_at',
            # 'estimated_price',          # ✅ uncommented
            'manifest_id', 'services_subtotal',
            'platform_fee', 'delivery_charge', 'discount', 'promo_code',
            'gst', 'cess', 'grand_total', 'payment_status', 'payment_method',
        ]
        read_only_fields = ['id', 'customer', 'status', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField())
    def get_customer_name(self, obj) -> str:
        return obj.customer.get_full_name() or obj.customer.email

    @extend_schema_field(serializers.CharField())
    def get_garage_name(self, obj) -> str:
        return obj.garage.name


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Booking
        fields = [
            # ── Existing booking fields ───────────────────────────────────
            'garage',
            'date',
            'time',
            'vehicle_type',
            'bike_details',
            'selected_services',
            # 'estimated_price',       # ✅ added

            # ── Billing fields ────────────────────────────────────────────
            'manifest_id',           # ✅ all billing fields added
            'services_subtotal',
            'platform_fee',
            'delivery_charge',
            'discount',
            'promo_code',
            'gst',
            'cess',
            'grand_total',
            'payment_status',
            'payment_method',
        ]

    def create(self, validated_data):
        return Booking.objects.create(**validated_data)


class RejectSerializer(serializers.Serializer):
    rejection_note = serializers.CharField(required=False, allow_blank=True)


class DurationSerializer(serializers.Serializer):
    estimated_duration_min = serializers.IntegerField(min_value=1)