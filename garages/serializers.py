"""garages/serializers.py"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Garage, GarageSchedule, ServiceOffer, CuratedService


class GarageScheduleSerializer(serializers.ModelSerializer):
    # camelCase for frontend (React Native)
    isOpen          = serializers.BooleanField(source='is_open')
    startHour       = serializers.IntegerField(source='start_hour')
    endHour         = serializers.IntegerField(source='end_hour')
    intervalMinutes = serializers.IntegerField(source='interval_minutes')

    class Meta:
        model  = GarageSchedule
        fields = ['day', 'isOpen', 'startHour', 'endHour', 'intervalMinutes']


class GarageSerializer(serializers.ModelSerializer):
    schedule = GarageScheduleSerializer(many=True, read_only=True)

    class Meta:
        model  = Garage
        fields = [
            'id', 'name', 'address', 'phone',
            'latitude', 'longitude',
            'services', 'service_prices', 'schedule',
            'photo', 'is_active',
        ]
        read_only_fields = ['id']


class GarageListSerializer(serializers.ModelSerializer):
    schedule    = GarageScheduleSerializer(many=True, read_only=True)
    distance_km = serializers.FloatField(read_only=True, default=None)

    class Meta:
        model  = Garage
        fields = [
            'id', 'name', 'address', 'phone',
            'latitude', 'longitude', 'distance_km',
            'services', 'service_prices', 'schedule',
            'photo', 'is_active',
        ]



class ServiceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ServiceOffer
        fields = ['id', 'title', 'subtitle', 'image_url', 'bg_color']


class CuratedServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CuratedService
        fields = ['id', 'name', 'icon', 'vehicle_type']