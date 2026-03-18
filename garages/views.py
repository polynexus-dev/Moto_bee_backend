"""garages/views.py"""
import math
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import Garage, DaySchedule, ServiceOffer, CuratedService
from .serializers import (
    GarageListSerializer, GarageDetailSerializer, GarageCreateUpdateSerializer,
    GarageServicesSerializer, DayScheduleSerializer, DayScheduleWriteSerializer,
    ServiceOfferSerializer, CuratedServiceSerializer,
)
from .permissions import IsOwner


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ─── Garages ──────────────────────────────────────────────────

class GarageListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        return GarageCreateUpdateSerializer if self.request.method == 'POST' else GarageListSerializer

    def get_queryset(self):
        qs = Garage.objects.filter(is_active=True).select_related('owner')
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, description='Latitude for distance sort'),
            OpenApiParameter('lon', float, description='Longitude for distance sort'),
            OpenApiParameter('radius', float, description='Radius in km (default 50)'),
            OpenApiParameter('q', str, description='Search by garage name'),
        ],
        responses={200: GarageListSerializer(many=True)},
        tags=['Garages'],
        summary='List all garages. Pass lat/lon to sort by distance.',
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = float(request.query_params.get('radius', 50))
        garages = list(qs)
        if lat and lon:
            lat, lon = float(lat), float(lon)
            for g in garages:
                g.distance_km = round(haversine(lat, lon, g.latitude, g.longitude), 2)
            garages = [g for g in garages if g.distance_km <= radius]
            garages.sort(key=lambda g: g.distance_km)
        return Response(GarageListSerializer(garages, many=True).data)

    @extend_schema(
        request=GarageCreateUpdateSerializer,
        responses={201: GarageDetailSerializer},
        tags=['Garages'],
        summary='Create a garage (owner only)',
    )
    def create(self, request, *args, **kwargs):
        if request.user.role != 'owner':
            return Response({'detail': 'Only owners can create a garage.'}, status=403)
        serializer = GarageCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        garage = serializer.save(owner=request.user)
        return Response(GarageDetailSerializer(garage).data, status=status.HTTP_201_CREATED)


class GarageDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Garage.objects.all()

    def get_serializer_class(self):
        return GarageCreateUpdateSerializer if self.request.method == 'PATCH' else GarageDetailSerializer

    @extend_schema(responses={200: GarageDetailSerializer}, tags=['Garages'], summary='Get garage detail')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=GarageCreateUpdateSerializer,
        responses={200: GarageDetailSerializer},
        tags=['Garages'],
        summary='Update garage info (owner only)',
    )
    def patch(self, request, *args, **kwargs):
        garage = self.get_object()
        if garage.owner != request.user:
            return Response({'detail': 'Forbidden.'}, status=403)
        return super().patch(request, *args, **kwargs)


class MyGarageView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        responses={200: GarageDetailSerializer},
        tags=['Garages'],
        summary='Get the garage owned by the logged-in owner',
    )
    def get(self, request):
        garage = get_object_or_404(Garage, owner=request.user)
        return Response(GarageDetailSerializer(garage).data)


class GarageServicesView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(
        request=GarageServicesSerializer,
        responses={200: GarageDetailSerializer},
        tags=['Garages'],
        summary='Update bike and scooty services list',
    )
    def patch(self, request, pk):
        garage = get_object_or_404(Garage, pk=pk, owner=request.user)
        serializer = GarageServicesSerializer(garage, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GarageDetailSerializer(garage).data)


# ─── Schedule ─────────────────────────────────────────────────

class ScheduleListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DayScheduleSerializer(many=True)},
        tags=['Schedule'],
        summary='Get full schedule for a garage',
    )
    def get(self, request, garage_id):
        garage = get_object_or_404(Garage, pk=garage_id)
        schedules = DaySchedule.objects.filter(garage=garage).order_by('date')
        return Response(DayScheduleSerializer(schedules, many=True).data)


class ScheduleDateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DayScheduleSerializer},
        tags=['Schedule'],
        summary='Get slots for a specific date',
    )
    def get(self, request, garage_id, date):
        garage = get_object_or_404(Garage, pk=garage_id)
        schedule = get_object_or_404(DaySchedule, garage=garage, date=date)
        return Response(DayScheduleSerializer(schedule).data)

    @extend_schema(
        request=DayScheduleWriteSerializer,
        responses={200: DayScheduleSerializer, 201: DayScheduleSerializer},
        tags=['Schedule'],
        summary='Create or update day schedule (owner only)',
    )
    def put(self, request, garage_id, date):
        garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)
        schedule, created = DaySchedule.objects.get_or_create(garage=garage, date=date)
        serializer = DayScheduleWriteSerializer(schedule, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            DayScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description='Day marked as closed')},
        tags=['Schedule'],
        summary='Mark a day as closed (owner only)',
    )
    def delete(self, request, garage_id, date):
        garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)
        schedule = get_object_or_404(DaySchedule, garage=garage, date=date)
        schedule.is_open = False
        schedule.slots = []
        schedule.save()
        return Response({'detail': f'{date} marked as closed.'})


# ─── Services ─────────────────────────────────────────────────

class ServiceOffersView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceOfferSerializer
    queryset = ServiceOffer.objects.filter(is_active=True)

    @extend_schema(tags=['Services'], summary='Promotional offer slides for home screen')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CuratedServicesView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CuratedServiceSerializer
    queryset = CuratedService.objects.filter(is_active=True)

    @extend_schema(tags=['Services'], summary='Quick-access service tiles for home screen')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ServiceSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter('q', str, description='Search term e.g. oil')],
        responses={200: GarageListSerializer(many=True)},
        tags=['Services'],
        summary='Search services across all garages',
    )
    def get(self, request):
        q = request.query_params.get('q', '').lower()
        if not q:
            return Response([])
        results = []
        for garage in Garage.objects.filter(is_active=True):
            matched_bike   = [s for s in garage.bike_services   if q in s.lower()]
            matched_scooty = [s for s in garage.scooty_services if q in s.lower()]
            if matched_bike or matched_scooty:
                results.append({
                    'garage_id':   str(garage.id),
                    'garage_name': garage.name,
                    'address':     garage.address,
                    'matched_services': {
                        'bike':   matched_bike,
                        'scooty': matched_scooty,
                    },
                })
        return Response(results)