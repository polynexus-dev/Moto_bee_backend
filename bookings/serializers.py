"""bookings/serializers.py"""
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
        model = Booking
        fields = ['garage', 'date', 'time', 'vehicle_type', 'bike_details', 'selected_services']

    def validate(self, data):
        from garages.models import DaySchedule
        try:
            schedule = DaySchedule.objects.get(garage=data['garage'], date=data['date'])
        except DaySchedule.DoesNotExist:
            raise serializers.ValidationError("No schedule exists for this date.")
        slot_id = data['time'].replace(':', '')
        slot = next((s for s in schedule.slots if s['id'] == slot_id), None)
        if not slot:
            raise serializers.ValidationError(f"Slot {data['time']} does not exist.")
        if slot['is_booked']:
            raise serializers.ValidationError(f"Slot {data['time']} is already booked.")
        return data

    def create(self, validated_data):
        from garages.models import DaySchedule
        booking = Booking.objects.create(**validated_data)
        try:
            schedule = DaySchedule.objects.get(garage=booking.garage, date=booking.date)
            slot_id = booking.time.replace(':', '')
            schedule.mark_slot_booked(slot_id, str(booking.customer.uid))
        except DaySchedule.DoesNotExist:
            pass
        return booking


class RejectSerializer(serializers.Serializer):
    rejection_note = serializers.CharField(required=False, allow_blank=True)


class DurationSerializer(serializers.Serializer):
    estimated_duration_min = serializers.IntegerField(min_value=1)