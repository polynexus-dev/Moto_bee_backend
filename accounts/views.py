"""accounts/views.py — Auth endpoints"""
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    RegisterSerializer, UserSerializer, UpdateProfileSerializer,
    LoginSerializer, LoginResponseSerializer, LogoutSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: LoginResponseSerializer},
        tags=['Auth'],
        summary='Register a new user (customer or owner)',
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        tags=['Auth'],
        summary='Login with email and password — returns JWT tokens',
    )
    def post(self, request):
        from django.contrib.auth import authenticate
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={205: OpenApiResponse(description='Logged out successfully')},
        tags=['Auth'],
        summary='Logout — blacklists the refresh token',
    )
    def post(self, request):
        try:
            token = RefreshToken(request.data['refresh'])
            token.blacklist()
            return Response({'detail': 'Logged out.'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(
        responses={200: UserSerializer},
        tags=['Auth'],
        summary='Get current logged-in user profile',
    )
    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        request=UpdateProfileSerializer,
        responses={200: UserSerializer},
        tags=['Auth'],
        summary='Update name, phone, or expo push token',
    )
    def patch(self, request, *args, **kwargs):
        serializer = UpdateProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)