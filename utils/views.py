"""utils/views.py — Location & utility endpoints"""
import math
import urllib.request
import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from garages.models import Garage
from garages.serializers import GarageListSerializer


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


class ReverseGeocodeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, required=True, description='Latitude'),
            OpenApiParameter('lon', float, required=True, description='Longitude'),
        ],
        tags=['Utils'],
        summary='Convert coordinates to a human-readable address (OpenStreetMap)',
    )
    def get(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({'detail': 'lat and lon are required.'}, status=400)
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MOTOBEE/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            return Response({
                'lat': float(lat),
                'lon': float(lon),
                'address': data.get('display_name', ''),
                'city': data.get('address', {}).get('city', ''),
                'state': data.get('address', {}).get('state', ''),
            })
        except Exception as e:
            return Response({'detail': f'Geocoding failed: {str(e)}'}, status=503)


class NearbyGaragesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, required=True, description='Latitude'),
            OpenApiParameter('lon', float, required=True, description='Longitude'),
            OpenApiParameter('radius', float, description='Radius in km (default 5)'),
        ],
        responses={200: GarageListSerializer(many=True)},
        tags=['Utils'],
        summary='Get garages within N km of given coordinates',
    )
    def get(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = float(request.query_params.get('radius', 5))
        if not lat or not lon:
            return Response({'detail': 'lat and lon are required.'}, status=400)
        lat, lon = float(lat), float(lon)
        garages = list(Garage.objects.filter(is_active=True))
        nearby = []
        for g in garages:
            dist = haversine(lat, lon, g.latitude, g.longitude)
            if dist <= radius:
                g.distance_km = round(dist, 2)
                nearby.append(g)
        nearby.sort(key=lambda g: g.distance_km)
        return Response(GarageListSerializer(nearby, many=True).data)