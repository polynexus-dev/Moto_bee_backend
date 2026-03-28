from rest_framework import serializers
from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vehicle
        fields = [
            'id',
            'type',
            'brand',
            'model',
            'year',
            'registration',
            'color',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']