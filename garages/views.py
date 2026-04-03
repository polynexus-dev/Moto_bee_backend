"""garages/views.py"""
import math
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import Garage, GarageSchedule, WEEKDAYS, ServiceOffer, CuratedService
from .serializers import (
    GarageSerializer, GarageListSerializer,
    GarageScheduleSerializer,
    ServiceOfferSerializer, CuratedServiceSerializer,
)


def haversine(lat1, lon1, lat2, lon2):
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def get_or_create_garage(user):
    """Get or silently create a blank garage for this owner."""
    garage, _ = Garage.objects.get_or_create(
        owner=user,
        defaults={'name': '', 'address': '', 'phone': ''}
    )
    return garage


# ─── GET /garages/       list all garages
# ─── POST /garages/      create garage
class GarageListView(generics.ListCreateAPIView):
    serializer_class = GarageSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return Garage.objects.prefetch_related('schedule').all()

    @extend_schema(
        parameters=[
            OpenApiParameter('lat',    float, description='Latitude for distance sort'),
            OpenApiParameter('lon',    float, description='Longitude for distance sort'),
            OpenApiParameter('radius', float, description='Radius in km (default 50)'),
            OpenApiParameter('q',      str,   description='Search by name'),
        ],
        responses={200: GarageListSerializer(many=True)},
        tags=['Garages'],
        summary='List all garages',
    )
    def list(self, request, *args, **kwargs):
        qs      = self.get_queryset()
        q       = request.query_params.get('q')
        lat     = request.query_params.get('lat')
        lon     = request.query_params.get('lon')
        radius  = float(request.query_params.get('radius', 50))

        if q:
            qs = qs.filter(name__icontains=q)

        garages = list(qs)
        if lat and lon:
            lat, lon = float(lat), float(lon)
            for g in garages:
                g.distance_km = round(haversine(lat, lon, g.latitude, g.longitude), 2)
            garages = [g for g in garages if g.distance_km <= radius]
            garages.sort(key=lambda g: g.distance_km)

        return Response(GarageListSerializer(garages, many=True).data)

    @extend_schema(
        request=GarageSerializer,
        responses={201: GarageSerializer},
        tags=['Garages'],
        summary='Create garage (owner only)',
    )
    def perform_create(self, serializer):
        if Garage.objects.filter(owner=self.request.user).exists():
            raise ValidationError('A garage already exists for this owner.')
        serializer.save(owner=self.request.user)


# ─── GET   /garages/mine/   owner fetches own garage
# ─── PATCH /garages/mine/   owner updates garage info
class MyGarageView(generics.RetrieveUpdateAPIView):
    serializer_class   = GarageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'patch']

    @extend_schema(tags=['Garages'], summary='Get my garage')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Garages'], summary='Update my garage details')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return get_or_create_garage(self.request.user)


# ─── PATCH /garages/mine/services/   owner updates services
class GarageServicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Garages'],
        summary='Update bike/scooty services and their prices',
        request=GarageSerializer,
        responses={200: GarageSerializer},
    )
    def patch(self, request):
        garage = get_or_create_garage(request.user)

        if 'services' in request.data:
            garage.services = request.data['services']

        if 'service_prices' in request.data:
            garage.service_prices = request.data['service_prices']

        garage.save()
        return Response(GarageSerializer(garage).data)


# ─── GET   /garages/{garage_id}/schedule/   fetch schedule
# ─── PATCH /garages/{garage_id}/schedule/   save schedule
class GarageScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_garage(self, garage_id, user):
        try:
            garage = Garage.objects.get(pk=garage_id)
        except Garage.DoesNotExist:
            raise NotFound(f'Garage with id {garage_id} not found.')
        if garage.owner != user:
            raise PermissionDenied('You do not have permission to access this garage.')
        return garage

    @extend_schema(
        responses={200: GarageScheduleSerializer(many=True)},
        tags=['Schedule'],
        summary='Get weekly schedule for a garage',
    )
    def get(self, request, garage_id):
        garage   = self._get_garage(garage_id, request.user)
        schedule = GarageSchedule.objects.filter(garage=garage).order_by('id')
        return Response(GarageScheduleSerializer(schedule, many=True).data)

    @extend_schema(
        tags=['Schedule'],
        summary='Update weekly schedule (owner only)',
        request=GarageScheduleSerializer(many=True),
        responses={200: GarageScheduleSerializer(many=True)},
    )
    def patch(self, request, garage_id):
        garage        = self._get_garage(garage_id, request.user)
        schedule_data = request.data.get('schedule', [])

        if not isinstance(schedule_data, list):
            raise ValidationError({'schedule': 'Must be a list of day objects.'})
        if not schedule_data:
            raise ValidationError({'schedule': 'Schedule list cannot be empty.'})

        valid_days = {d[0] for d in WEEKDAYS}

        with transaction.atomic():
            for item in schedule_data:
                day = item.get('day')
                if not day:
                    raise ValidationError({'day': 'Each entry must include a day field.'})
                if day not in valid_days:
                    raise ValidationError({'day': f'"{day}" is not a valid weekday.'})

                is_open    = item.get('isOpen', False)
                start_hour = item.get('startHour', 9)
                end_hour   = item.get('endHour', 18)

                if is_open and end_hour <= start_hour:
                    raise ValidationError({
                        'schedule': f'{day}: closing time must be after opening time.'
                    })

                GarageSchedule.objects.update_or_create(
                    garage=garage,
                    day=day,
                    defaults={
                        'is_open':          is_open,
                        'start_hour':       start_hour,
                        'end_hour':         end_hour,
                        'interval_minutes': item.get('intervalMinutes', 60),
                    }
                )

        updated = GarageSchedule.objects.filter(garage=garage).order_by('id')
        return Response(GarageScheduleSerializer(updated, many=True).data)


# ─── GET /garages/{id}/ & PATCH  single garage detail for customer
class GarageDetailView(generics.RetrieveUpdateAPIView):
    serializer_class  = GarageSerializer
    queryset          = Garage.objects.prefetch_related('schedule').all()
    lookup_field      = 'id'
    http_method_names = ['get', 'patch']

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_update(self, serializer):
        garage = self.get_object()
        if garage.owner != self.request.user:
            raise PermissionDenied('You do not own this garage.')
        serializer.save()

    @extend_schema(tags=['Garages'], summary='Get garage detail')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Garages'], summary='Update garage details (owner only)')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

# ─── Services ─────────────────────────────────────────────────

class ServiceOffersView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class   = ServiceOfferSerializer
    queryset           = ServiceOffer.objects.filter(is_active=True)

    @extend_schema(tags=['Services'], summary='Promo banners for home screen')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CuratedServicesView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class   = CuratedServiceSerializer
    queryset           = CuratedService.objects.filter(is_active=True)

    @extend_schema(tags=['Services'], summary='Quick-service tiles for home screen')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ServiceSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter('q', str, description='Search term e.g. oil')],
        tags=['Services'],
        summary='Search services across all garages',
    )
    def get(self, request):
        q = request.query_params.get('q', '').lower()
        if not q:
            return Response([])
        results = []
        for garage in Garage.objects.all():
            bike   = garage.services.get('bike',   [])
            scooty = garage.services.get('scooty', [])
            matched_bike   = [s for s in bike   if q in s.lower()]
            matched_scooty = [s for s in scooty if q in s.lower()]
            if matched_bike or matched_scooty:
                results.append({
                    'garage_id':        str(garage.id),
                    'garage_name':      garage.name,
                    'address':          garage.address,
                    'matched_services': {
                        'bike':   matched_bike,
                        'scooty': matched_scooty,
                    },
                })
        return Response(results)