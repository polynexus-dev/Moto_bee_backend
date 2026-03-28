from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Vehicle
from .serializers import VehicleSerializer


class VehicleListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /vehicles/
    def get(self, request):
        vehicles = Vehicle.objects.filter(owner=request.user)
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data)

    # POST /vehicles/
    def post(self, request):
        serializer = VehicleSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VehicleUpdateDeleteView(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, user, pk):
        return get_object_or_404(Vehicle, id=pk, owner=user)

    # PATCH /vehicles/{id}/
    def patch(self, request, pk):

        vehicle = self.get_object(request.user, pk)

        serializer = VehicleSerializer(
            vehicle,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE /vehicles/{id}/
    def delete(self, request, pk):

        vehicle = self.get_object(request.user, pk)
        vehicle.delete()

        return Response(
            {"message": "Vehicle deleted successfully"},
            status=status.HTTP_200_OK
        )