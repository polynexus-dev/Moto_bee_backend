from rest_framework import serializers
from .models import UserLocationProfile

class UserLocationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserLocationProfile
        fields = [
            'id', 'type', 'label', 'address',
            'latitude', 'longitude',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']