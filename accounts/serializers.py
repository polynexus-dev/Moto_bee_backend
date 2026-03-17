"""accounts/serializers.py"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['uid', 'name', 'email', 'phone', 'role']

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'password', 'role']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        name = validated_data.pop('name', '')
        parts = name.split(' ', 1)
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone=validated_data.get('phone', ''),
            role=validated_data.get('role', 'customer'),
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else '',
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UpdateProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['name', 'phone', 'expo_push_token']

    def update(self, instance, validated_data):
        name = validated_data.pop('name', None)
        if name:
            parts = name.split(' ', 1)
            instance.first_name = parts[0]
            instance.last_name = parts[1] if len(parts) > 1 else ''
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance