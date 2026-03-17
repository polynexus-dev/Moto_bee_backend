"""garages/serializers.py"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Garage, DaySchedule, ServiceOffer, CuratedService


class GarageListSerializer(serializers.ModelSerializer):
    services    = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(read_only=True, default=None)
    owner_name  = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'phone',
            'latitude', 'longitude', 'distance_km',
            'services', 'owner_name', 'photo', 'is_active',
        ]

    @extend_schema_field(serializers.DictField())
    def get_services(self, obj) -> dict:
        return {'bike': obj.bike_services, 'scooty': obj.scooty_services}

    @extend_schema_field(serializers.CharField())
    def get_owner_name(self, obj) -> str:
        return obj.owner.get_full_name() or obj.owner.username


class GarageDetailSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'phone',
            'latitude', 'longitude',
            'bike_services', 'scooty_services', 'services',
            'photo', 'is_active', 'created_at',
        ]

    @extend_schema_field(serializers.DictField())
    def get_services(self, obj) -> dict:
        return {'bike': obj.bike_services, 'scooty': obj.scooty_services}


class GarageCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'phone',
            'latitude', 'longitude',
            'bike_services', 'scooty_services', 'photo',
        ]


class GarageServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garage
        fields = ['bike_services', 'scooty_services']


class SlotSerializer(serializers.Serializer):
    id        = serializers.CharField()
    time      = serializers.CharField()
    is_booked = serializers.BooleanField()
    booked_by = serializers.CharField(allow_null=True)


class DayScheduleSerializer(serializers.ModelSerializer):
    slots = SlotSerializer(many=True, read_only=True)

    class Meta:
        model = DaySchedule
        fields = ['date', 'is_open', 'start_hour', 'end_hour', 'interval_minutes', 'slots']


class DayScheduleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DaySchedule
        fields = ['is_open', 'start_hour', 'end_hour', 'interval_minutes']

    def update(self, instance, validated_data):
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.slots = instance.generate_slots() if instance.is_open else []
        instance.save()
        return instance

    def create(self, validated_data):
        instance = DaySchedule(**validated_data)
        instance.slots = instance.generate_slots() if instance.is_open else []
        instance.save()
        return instance


class ServiceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffer
        fields = ['id', 'title', 'subtitle', 'image_url', 'bg_color']


class CuratedServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuratedService
        fields = ['id', 'name', 'icon', 'vehicle_type']