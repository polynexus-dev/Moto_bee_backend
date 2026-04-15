# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from .models import UserLocationProfile
from .serializers import UserLocationProfileSerializer


class UserLocationProfileListView(APIView):
    """
    GET  /location-profile/      → list all profiles for the authenticated user
    POST /location-profile/      → create a new profile
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profiles = UserLocationProfile.objects.filter(user=request.user)
        serializer = UserLocationProfileSerializer(profiles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserLocationProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("ERRORS:", serializer.errors)  # <-- and this
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLocationProfileDetailView(APIView):
    """
    GET    /location-profile/<pk>/   → retrieve a single profile
    PUT    /location-profile/<pk>/   → full update
    PATCH  /location-profile/<pk>/   → partial update
    DELETE /location-profile/<pk>/   → delete
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(UserLocationProfile, pk=pk, user=user)

    def get(self, request, pk):
        profile = self.get_object(pk, request.user)
        serializer = UserLocationProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        profile = self.get_object(pk, request.user)
        serializer = UserLocationProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        profile = self.get_object(pk, request.user)
        serializer = UserLocationProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        profile = self.get_object(pk, request.user)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)